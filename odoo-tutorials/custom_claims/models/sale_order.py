from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    claim_ids = fields.One2many(
        comodel_name='custom.claim',
        inverse_name='sale_order_id',
        string='Reclamacions',
        copy=False
    )