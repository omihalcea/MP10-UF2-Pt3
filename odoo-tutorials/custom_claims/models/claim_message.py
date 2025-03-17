
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

    is_system_message = fields.Boolean(
    string='Missatge del sistema',
    default=False,
    help="Indica si el missatge va ser generat automàticament pel sistema"
    )

    # Data de creació de la reclamació
    create_date = fields.Datetime(
        string='Data creació',
        readonly=True  # Només de lectura
    )

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)
        for message in messages:
            # Solo si es un mensaje manual (no notificación del sistema)
            if message.message_type == 'comment': 
                claim = message.claim_id
                if claim.state == 'new':
                    claim.write({'state': 'in_progress'})
        return messages

        
    def write(self, vals):
        raise exceptions.UserError(_('Els missatges són immutables'))
    
    def unlink(self):
        raise exceptions.UserError(_('Els missatges no es poden eliminar'))