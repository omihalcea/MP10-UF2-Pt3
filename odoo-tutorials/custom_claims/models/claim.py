# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from datetime import datetime

class Claim(models.Model):
    _name = 'custom.claim'
    _description = 'Reclamació de client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Referència',
        readonly=True,
        default=lambda self: _('Nova'),
        copy=False
    )
    subject = fields.Char(
        string='Assumpte',
        required=True,
        tracking=True
    )
    description = fields.Text(
        string='Descripció inicial',
        required=True
    )
    state = fields.Selection(
        selection=[
            ('new', 'Nova'),
            ('in_progress', 'En tractament'),
            ('closed', 'Tancada'),
            ('canceled', 'Cancel·lada')],
        string='Estat',
        default='new',
        tracking=True
    )
    sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Comanda associada',
        required=True,
        domain="[('state','not in', ('cancel', 'done'))]",
        ondelete='restrict'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Client',
        related='sale_order_id.partner_id', 
        store=True,
        readonly=True
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsable',
        default=lambda self: self.env.user,
        tracking=True
    )
    create_date = fields.Datetime(
        string='Data creació',
        readonly=True
    )
    write_date = fields.Datetime(
        string='Data modificació',
        readonly=True
    )
    close_date = fields.Datetime(
        string='Data tancament',
        readonly=True
    )
    message_ids = fields.One2many(
        comodel_name='custom.claim.message',
        inverse_name='claim_id',
        string='Missatges',
        copy=False
    )
    invoice_count = fields.Integer(
        string='Factures',
        compute='_compute_invoice_shipment'
    )
    shipment_count = fields.Integer(
        string='Enviaments',
        compute='_compute_invoice_shipment'
    )
    resolution = fields.Text(
        string='Resolució final',
        tracking=True
    )
    closure_reason_id = fields.Many2one(
        comodel_name='custom.closure.reason',
        string='Motiu tancament',
        tracking=True
    )

    @api.depends('sale_order_id.invoice_ids', 'sale_order_id.picking_ids')
    def _compute_invoice_shipment(self):
        for record in self:
            record.invoice_count = len(record.sale_order_id.invoice_ids.filtered(lambda i: i.state != 'cancel')) if record.sale_order_id else 0
            record.shipment_count = len(record.sale_order_id.picking_ids.filtered(lambda p: p.state != 'cancel')) if record.sale_order_id else 0
    
    @api.depends('message_ids')
    def _compute_state_based_on_messages(self):
        for record in self:
            if record.message_ids and record.state == 'new':
                record.state = 'in_progress'

    @api.model
    def create(self, vals):
        if vals.get('name', _('Nova')) == _('Nova'):
            seq = self.env['ir.sequence'].next_by_code('custom.claim')
            vals['name'] = seq or _('Nova')
            if not seq:
                raise exceptions.ValidationError(_('No s’ha pogut generar la seqüència per a les reclamacions.'))
        return super().create(vals)

    @api.constrains('sale_order_id', 'state')
    def _check_open_claims(self):
        for record in self:
            if record.state in ['new', 'in_progress']:
                existing = self.search([
                    ('sale_order_id', '=', record.sale_order_id.id),
                    ('state', 'in', ('new', 'in_progress')),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing:
                    raise exceptions.ValidationError(
                        _('Ja existeix una reclamació activa per la comanda %s') % record.sale_order_id.name)
                    
    def action_close(self):
        """ Tanca la reclamació i actualitza la data de tancament."""
        for record in self:
            if record.state not in ['closed', 'canceled']:
                record.write({
                    'state': 'closed',
                    'close_date': fields.Datetime.now(),
                })
        return True