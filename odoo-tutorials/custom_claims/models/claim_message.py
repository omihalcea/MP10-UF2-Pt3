
from odoo import models, fields, api, exceptions, _

class ClaimMessage(models.Model):
    _name = 'custom.claim.message'
    _description = 'Missatge de reclamació'
    _order = 'create_date desc'
    _rec_name = 'create_date'

    claim_id = fields.Many2one(
        comodel_name='custom.claim',
        string='Reclamació',
        required=True,
        ondelete='cascade',
        readonly=True
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
   
    message_type = fields.Selection(
        selection=[
            ('comment', 'Comentari'),
            ('user_notification', 'Notificació d\'usuari')
        ],
        string='Tipus de missatge',
        default='comment'
    )

    @api.model
    def create(self, vals):
        # Crea el missatge
        message = super().create(vals)
        
        # Canvia l'estat de la reclamació associada a "En tractament" si està en estat "Nova"
        if message.claim_id.state == 'new':
            message.claim_id.write({'state': 'in_progress'})
        
        return message

        
    def write(self, vals):
        raise exceptions.UserError(_('Els missatges són immutables'))
    
    def unlink(self):
        raise exceptions.UserError(_('Els missatges no es poden eliminar'))