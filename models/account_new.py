# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
# __author__ = jeff@openerp.cn
# __author__ = cysnake4713@gmail.com

from openerp import models, fields, api, exceptions
from openerp.tools.translate import _


class AccountMove(models.Model):
    _inherit = 'account.move'
    """
    添加制单、审核、附件数三个字段
    """
    proof = fields.Integer('Attachment Count', required=False, default=1)

    """
    附件数默认为1张
    凭证业务类型默认为总帐
    """
    _defaults = {
        'journal_id': lambda self, cr, uid, context: self.pool.get('account.journal').search(cr, uid, [('type', '=', 'general')], limit=1)[0],
    }


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    currency_rate = fields.Float('Currency Rate', digits=(10, 6), compute='_compute_currency_rate')

    @api.depends('credit', 'debit', 'amount_currency')
    def _compute_currency_rate(self):
        for record in self:
            if record.currency_id:
                if record.amount_currency:
                    record.currency_rate = abs((record.debit or record.credit) / record.amount_currency)
                else:
                    record.currency_rate = False


class AccountPeriod(models.Model):
    _name = 'account.period'
    _inherit = 'account.period'

    @api.cr_uid
    def build_ctx_periods_in_company(self, cr, uid, period_from_id, period_to_id):
        if period_from_id == period_to_id:
            return [period_from_id]
        period_from = self.browse(cr, uid, period_from_id)
        period_date_start = period_from.date_start
        company1_id = period_from.company_id.id
        period_to = self.browse(cr, uid, period_to_id)
        period_date_stop = period_to.date_stop
        company2_id = period_to.company_id.id
        if company1_id != company2_id:
            raise exceptions.Warning(_('Error!'), _('You should choose the periods that belong to the same company.'))
        if period_date_start > period_date_stop:
            raise exceptions.Warning(_('Error!'), _('Start period should precede then end period.'))

        # /!\ We do not include a criterion on the company_id field below, to allow producing consolidated reports
        # on multiple companies. It will only work when start/end periods are selected and no fiscal year is chosen.

        # for period from = january, we want to exclude the opening period (but it has same date_from,
        # so we have to check if period_from is special or not to include that clause or not in the search).
        if period_from.special:
            return self.search(cr, uid,
                               [('date_start', '>=', period_date_start), ('date_stop', '<=', period_date_stop), ('company_id', '=', company2_id)])
        return self.search(cr, uid, [('date_start', '>=', period_date_start), ('date_stop', '<=', period_date_stop), ('special', '=', False),
                                     ('company_id', '=', company2_id)])
