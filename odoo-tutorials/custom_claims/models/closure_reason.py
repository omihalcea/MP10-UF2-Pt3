# -*- coding: utf-8 -*-

from odoo import models, fields

class ClosureReason(models.Model):
    _name = 'custom.closure.reason'
    _description = 'Motius de tancament'
    _order = 'name asc'

    name = fields.Char('Motiu', required=True, translate=True)
    code = fields.Char('Codi', required=True, size=10)
    active = fields.Boolean('Actiu', default=True)