# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError
from datetime import datetime

class Claim(models.Model):
    # Nom del model a Odoo
    _name = 'custom.claim'
    # Descripció del model
    _description = 'Reclamació de client'
    # Heretem funcionalitats de missatgeria i activitats
    _inherit = ['mail.thread', 'mail.activity.mixin']
    # Ordenar les reclamacions per data de creació descendent
    _order = 'create_date desc'

    # Camp per a la referència de la reclamació
    name = fields.Char(
        string='Referència',
        readonly=True,
        default=lambda self: _('Nova'),  # Valor per defecte "Nova"
        copy=False  # No es copia en duplicar la reclamació
    )
    # Camp per a l'assumpte de la reclamació
    subject = fields.Char(
        string='Assumpte',
        required=True,  # És obligatori
        tracking=True  # Es rastreja per a historial de canvis
    )
    # Camp per a la descripció inicial de la reclamació
    description = fields.Text(
        string='Descripció inicial',
        required=True  # És obligatori
    )
    # Camp per a l'estat de la reclamació
    state = fields.Selection(
        selection=[
            ('new', 'Nova'),  # Estat inicial
            ('in_progress', 'En tractament'),  # Quan es comença a tractar
            ('closed', 'Tancada'),  # Quan es resol
            ('canceled', 'Cancel·lada')],  # Quan es cancel·la
        string='Estat',
        default='new',  # Estat per defecte
        tracking=True  # Es rastreja per a historial de canvis
    )
    # Relació amb la comanda de venda associada
    sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Comanda associada',
        required=True,  # És obligatori
        domain="[('state','not in', ('cancel', 'done'))]",  # Filtra comandes no cancel·lades o finalitzades
        ondelete='restrict'  # No es pot eliminar la comanda si té reclamacions
    )
    # Relació amb el client (automàticament relacionat amb la comanda de venda)
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Client',
        related='sale_order_id.partner_id',  # Relacionat amb el client de la comanda
        store=True,  # S'emmagatzema a la base de dades
        readonly=True  # Només de lectura
    )
    # Relació amb l'usuari responsable de la reclamació
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsable',
        default=lambda self: self.env.user,  # Per defecte, l'usuari actual
        tracking=True  # Es rastreja per a historial de canvis
    )
    # Data de creació de la reclamació
    create_date = fields.Datetime(
        string='Data creació',
        readonly=True  # Només de lectura
    )
    # Data de modificació de la reclamació
    write_date = fields.Datetime(
        string='Data modificació',
        readonly=True  # Només de lectura
    )
    # Data de tancament de la reclamació
    close_date = fields.Datetime(
        string='Data tancament',
        readonly=True  # Només de lectura
    )
    # Llista de missatges associats a la reclamació
    message_ids = fields.One2many(
        comodel_name='custom.claim.message',
        inverse_name='claim_id',
        string='Missatges',
        copy=False  # No es copien en duplicar la reclamació
    )
    # Nombre de factures associades a la comanda
    invoice_count = fields.Integer(
        string='Factures',
        compute='_compute_invoice_shipment'  # Calculat automàticament
    )
    # Nombre d'enviaments associats a la comanda
    shipment_count = fields.Integer(
        string='Enviaments',
        compute='_compute_invoice_shipment'  # Calculat automàticament
    )
    # Descripció de la resolució final de la reclamació
    resolution = fields.Text(
        string='Resolució final',
        tracking=True  # Es rastreja per a historial de canvis
    )
    # Motiu de tancament de la reclamació
    closure_reason_id = fields.Many2one(
        comodel_name='custom.closure.reason',
        string='Motiu tancament',
        tracking=True  # Es rastreja per a historial de canvis
    )

    # Mètode per calcular el nombre de factures i enviaments associats
    @api.depends('sale_order_id.invoice_ids', 'sale_order_id.picking_ids')
    def _compute_invoice_shipment(self):
        for record in self:
            # Comptar factures no cancel·lades
            record.invoice_count = len(record.sale_order_id.invoice_ids.filtered(lambda i: i.state != 'cancel')) if record.sale_order_id else 0
            # Comptar enviaments no cancel·lats
            record.shipment_count = len(record.sale_order_id.picking_ids.filtered(lambda p: p.state != 'cancel')) if record.sale_order_id else 0
    
    # Mètode per canviar l'estat a "En tractament" si hi ha missatges
    @api.depends('message_ids')  # <-- Asegúrate de que está decorado
    def _compute_state_based_on_messages(self):
        for record in self:
            if record.message_ids and record.state == 'new':
                record.state = 'in_progress'  # Actualiza solo si está en "new"


    # Mètode per generar una seqüència única per a la referència de la reclamació
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nova')) == _('Nova'):
                seq = self.env['ir.sequence'].next_by_code('custom.claim')
                vals['name'] = seq or _('Nova')
                if not seq:
                    raise exceptions.ValidationError(_('Error en la secuencia'))
        return super().create(vals_list)

    # Restricció per evitar dues reclamacions obertes per la mateixa comanda
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
                    
    # Mètode per tancar una reclamació
    def action_close(self):
        for record in self:
            if record.state in ['closed', 'canceled']:
                raise UserError(_('La reclamació ja està tancada o cancel·lada.'))
            
            record.write({
                'state': 'closed',
                'close_date': fields.Datetime.now(),
            })
            # Mensaje en el chatter
            record.message_post(
                body="✅ La reclamació ha estat tancada.",
                message_type='comment',
                subtype_xmlid='mail.mt_note'
            )
        return True
        
    # Mètode per cancel·lar una reclamació
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
            # Mensaje en el chatter
            record.message_post(
                body="❌ La reclamació ha estat cancel·lada.",
                message_type='comment',
                subtype_xmlid='mail.mt_note'
            )
        return True
    
    # Mètode per reobrir una reclamació
    def action_reopen(self):
        for record in self:
            if record.state not in ['closed', 'canceled']:
                raise UserError(_('Només es poden reobrir reclamacions tancades o cancel·lades.'))
            
            new_state = 'in_progress' if record.message_ids else 'new'
            record.write({
                'state': new_state,
                'close_date': False,
            })
            # Mensaje en el chatter
            record.message_post(
                body="🔄 La reclamació ha estat reoberta.",
                message_type='comment',
                subtype_xmlid='mail.mt_note'
            )
        return True

    # Mètode per cancel·lar la comanda de venda associada
    def action_cancel_order(self):
        for record in self:
            if not record.sale_order_id:
                raise UserError(_('No hi ha cap comanda de venda associada a aquesta reclamació.'))

            # Verificar si hi ha factures publicades
            if record.sale_order_id.invoice_ids.filtered(lambda inv: inv.state == 'posted'):
                raise UserError(_('No es pot cancel·lar la comanda perquè té factures publicades.'))

            # Cancel·lar la comanda de venda si no està ja cancel·lada o finalitzada
            if record.sale_order_id.state not in ['cancel', 'done']:
                record.sale_order_id._action_cancel()  # Utilitzem el mètode intern per cancel·lar la comanda

            # Cancel·lar les factures no publicades
            invoices_to_cancel = record.sale_order_id.invoice_ids.filtered(lambda inv: inv.state != 'posted')
            if invoices_to_cancel:
                invoices_to_cancel.button_cancel()

            # Cancel·lar els enviaments no fets
            pickings_to_cancel = record.sale_order_id.picking_ids.filtered(lambda p: p.state != 'done')
            if pickings_to_cancel:
                pickings_to_cancel.action_cancel()

            # Enviar correu al client utilitzant la plantilla per defecte d'Odoo
            template = self.env.ref('sale.mail_template_sale_cancellation', raise_if_not_found=False)
            if template:
                template.send_mail(record.sale_order_id.id, force_send=True)

            # Notificar al chatter de la comanda sobre la cancel·lació i l'enviament del correu
            record.sale_order_id.message_post(
                body=f"El client ha estat notificat per correu de la cancel·lació de la comanda {record.sale_order_id.name}.",
                message_type='comment',
                subtype_xmlid='mail.mt_note'
            )

            # Actualitzar l'estat de la reclamació si és necessari
            if record.state in ['new', 'in_progress']:
                record.write({
                    'state': 'canceled',
                    'close_date': fields.Datetime.now(),
                })

        return True