from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Claim(models.Model):
    _name = 'custom.claim'
    _description = 'Reclamació de Client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'subject'

    subject = fields.Char(string='Assumpte', required=True, tracking=True)
    description = fields.Text(string='Descripció Inicial', required=True)
    state = fields.Selection([
        ('new', 'Nova'),
        ('in_progress', 'En Tractament'),
        ('closed', 'Tancada'),
        ('cancelled', 'Cancel·lada')
    ], string='Estat', default='new', tracking=True)
    sale_order_id = fields.Many2one('sale.order', string='Comanda de Venda', required=True)
    partner_id = fields.Many2one('res.partner', string='Client', required=True)
    user_id = fields.Many2one('res.users', string='Usuari', default=lambda self: self.env.user)
    create_date = fields.Datetime(string='Data de Creació', default=fields.Datetime.now, readonly=True)
    write_date = fields.Datetime(string='Data de Modificació', readonly=True)
    close_date = fields.Datetime(string='Data de Tancament', readonly=True)
    message_ids = fields.One2many('custom.claim.message', 'claim_id', string='Missatges')
    invoice_count = fields.Integer(string='Nombre de Factures', compute='_compute_invoice_count')
    delivery_count = fields.Integer(string='Nombre d’Enviaments', compute='_compute_delivery_count')
    resolution = fields.Text(string='Descripció de la Resolució Final')
    closing_reason_id = fields.Many2one('custom.claim.closing.reason', string='Motiu de Tancament/Cancel·lació')

    _sql_constraints = [
        ('unique_open_claim_per_order', 'UNIQUE(sale_order_id, state)', 'Només pot haver-hi una reclamació oberta per comanda.')
    ]

    @api.depends('sale_order_id')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.sale_order_id.invoice_ids)

    @api.depends('sale_order_id')
    def _compute_delivery_count(self):
        for record in self:
            record.delivery_count = len(record.sale_order_id.picking_ids)

    def action_set_in_progress(self):
        self.ensure_one()
        if self.state == 'new':
            self.state = 'in_progress'

    def action_close(self):
        self.ensure_one()
        if self.state in ['new', 'in_progress']:
            if not self.resolution:
                raise ValidationError('Cal proporcionar una resolució abans de tancar la reclamació.')
            self.state = 'closed'
            self.close_date = fields.Datetime.now()

    def action_cancel(self):
        self.ensure_one()
        if self.state in ['new', 'in_progress']:
            self.state = 'cancelled'
            self.close_date = fields.Datetime.now()

    def action_reopen(self):
        self.ensure_one()
        if self.state in ['closed', 'cancelled']:
            self.state = 'in_progress'
            self.close_date = False

    def action_cancel_sale_order(self):
        self.ensure_one()
        sale_order = self.sale_order_id
        if sale_order.state == 'cancel':
            raise ValidationError('La comanda ja està cancel·lada.')
        if any(invoice.state == 'posted' for invoice in sale_order.invoice_ids):
            raise ValidationError('No es pot cancel·lar la comanda perquè té factures publicades.')
        sale_order.action_cancel()
        template = self.env.ref('custom_claims.email_template_sale_order_cancelled')
        self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)

class ClaimMessage(models.Model):
    _name = 'custom.claim.message'
    _description = 'Missatge de Reclamació'

    claim_id = fields.Many2one('custom.claim', string='Reclamació', required=True, ondelete='cascade')
    author_id = fields.Many2one('res.partner', string='Autor', required=True)
    date = fields.Datetime(string='Data', default=fields.Datetime.now, readonly=True)
    content = fields.Text(string='Contingut', required=True)

class ClaimClosingReason(models.Model):
    _name = 'custom.claim.closing.reason'
    _description = 'Motiu de Tancament/Cancel·lació'

    name = fields.Char(string='Motiu', required=True)

