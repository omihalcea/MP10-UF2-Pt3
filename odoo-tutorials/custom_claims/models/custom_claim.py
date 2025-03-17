from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError

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
            ('canceled', 'Cancel·lada')
        ],
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
    # Renombrem el camp dels missatges personalitzats per no interferir amb el chatter
    custom_message_ids = fields.One2many(
        comodel_name='custom.claim.message',
        inverse_name='claim_id',
        string='Missatges Personalitzats',
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nova')) == _('Nova'):
                seq = self.env['ir.sequence'].next_by_code('custom.claim')
                vals['name'] = seq or _('Nova')
                if not seq:
                    raise exceptions.ValidationError(_('Error en la secuencia'))
        return super().create(vals_list)

    # Els mètodes action_close, action_cancel i action_reopen segueixen utilitzant message_post()
    def action_close(self):
        for record in self:
            if record.state in ['closed', 'canceled']:
                raise UserError(_('La reclamació ja està tancada o cancel·lada.'))
            record.write({
                'state': 'closed',
                'close_date': fields.Datetime.now(),
            })
            record.message_post(
                body="✅ La reclamació ha estat tancada.",
                message_type='comment',
                subtype_xmlid='mail.mt_note'
            )
        return True

    def action_cancel(self):
        for record in self:
            if record.state == 'canceled':
                raise UserError(_('La reclamació ja està cancel·lada.'))
            if record.sale_order_id.invoice_ids.filtered(lambda inv: inv.state == 'posted'):
                raise UserError(_('No es pot cancel·lar perquè hi ha factures publicades.'))
            if record.sale_order_id:
                record.sale_order_id.action_cancel()
                invoices_to_cancel = record.sale_order_id.invoice_ids.filtered(lambda inv: inv.state != 'posted')
                invoices_to_cancel.button_cancel()
                pickings_to_cancel = record.sale_order_id.picking_ids.filtered(lambda p: p.state != 'done')
                pickings_to_cancel.action_cancel()
            record.write({
                'state': 'canceled',
                'close_date': fields.Datetime.now(),
            })
            message = f"❌ La reclamació {record.name} ha estat cancel·lada per {self.env.user.name} el {fields.Datetime.now().strftime('%d-%m-%Y %H:%M')}."
            record.message_post(
                body=message,
                message_type='comment',
                subtype_xmlid='mail.mt_note'
            )
        return True

    def action_reopen(self):
        for record in self:
            if record.state not in ['closed', 'canceled']:
                raise UserError(_('Només es poden reobrir reclamacions tancades o cancel·lades.'))
            new_state = 'in_progress'
            record.write({
                'state': new_state,
                'close_date': False,
            })
            record.message_post(
                body="🔄 La reclamació ha estat reoberta.",
                message_type='comment',
                subtype_xmlid='mail.mt_note'
            )
        return True
