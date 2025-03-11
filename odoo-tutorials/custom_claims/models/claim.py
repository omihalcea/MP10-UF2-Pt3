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


    @api.model
    def create(self, vals):
        if vals.get('name', _('Nova')) == _('Nova'):
            seq = self.env['ir.sequence'].next_by_code('custom.claim')
            vals['name'] = seq or _('Nova')
            if not seq:
                raise exceptions.ValidationError(_('No s’ha pogut generar la seqüència per a les reclamacions.'))
        return super().create(vals)


    def action_close(self):
        self.ensure_one()
        if self.state not in ['new', 'in_progress']:
            raise exceptions.UserError(_('Acció no permesa en estat actual'))
        self.write({
            'state': 'closed',
            'close_date': datetime.now(),
            'closure_reason_id': self.closure_reason_id.id if self.closure_reason_id else None
        })

    def action_cancel(self):
        self.ensure_one()
        if self.state == 'canceled':
            return
        self.write({'state': 'canceled'})

    def action_reopen(self):
        self.ensure_one()
        allowed_states = ['closed', 'canceled']
        if self.state not in allowed_states:
            raise exceptions.UserError(_('Només es poden reobrir reclamacions tancades o cancel·lades'))
        self.write({'state': 'in_progress'})

    def action_cancel_order(self):
        self.ensure_one()
        if self.sale_order_id.invoice_ids.filtered(lambda i: i.state == 'posted'):
            raise exceptions.UserError(_('Operació bloquejada: Existeixen factures validades'))
        
        if self.sale_order_id.picking_ids.filtered(lambda p: p.state == 'done'):
            raise exceptions.UserError(_('Operació bloquejada: Existeixen enviaments completats'))

        # Notificació al client
        template = self.env.ref('custom_claims.mail_template_order_cancellation', raise_if_not_found=False)
        if template:
            self.sale_order_id.message_post_with_template(template.id)

        # Cancel·lar operacions relacionades
        self.sale_order_id._action_cancel()
        self.sale_order_id.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')).action_cancel()
        self.sale_order_id.invoice_ids.filtered(lambda i: i.state == 'draft').button_cancel()


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


class ClaimMessage(models.Model):
    _name = 'custom.claim.message'
    _description = 'Missatge de reclamació'
    _order = 'create_date desc'
    _rec_name = 'create_date'

    claim_id = fields.Many2one(
        comodel_name='custom.claim',
        string='Reclamació',
        required=True,
        ondelete='cascade'
            default=lambda self: self._context.get('active_id')  # Assigna el claim_id automàticament si s'està creant des de la vista de reclamació
    )
    content = fields.Text(
        string='Contingut',
        required=True
    )
    author_id = fields.Many2one(
        comodel_name='res.users',
        string='Autor',
        default=lambda self: self.env.user,
        readonly=True
    )
    create_date = fields.Datetime(
        string='Data',
        default=fields.Datetime.now,
        readonly=True
    )

    def write(self, vals):
        raise exceptions.UserError(_('Els missatges són immutables'))
    
    def unlink(self):
        raise exceptions.UserError(_('Els missatges no es poden eliminar'))

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    claim_ids = fields.One2many(
        comodel_name='custom.claim',
        inverse_name='sale_order_id',
        string='Reclamacions',
        copy=False
    )