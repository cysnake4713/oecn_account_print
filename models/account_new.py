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
    company_id = fields.Many2one('res.company', readonly=True, related='journal_id.company_id')

    """
    附件数默认为1张
    凭证业务类型默认为总帐
    """
    _defaults = {
        'journal_id': lambda self, cr, uid, context: self.pool.get('account.journal').search(cr, uid, [('type', '=', 'general')], limit=1)[0],
    }

    @api.onchange('date', 'journal_id')
    def _onchange_date(self):
        if self.date and self.journal_id:
            self.period_id = self.env['account.period'].with_context(company_id=self.journal_id.company_id.id).find(dt=self.date)


class AccountMoveLine(models.Model):
    _name = 'account.move.line'
    _inherit = 'account.move.line'

    currency_rate = fields.Float('Currency Rate', digits=(10, 4))

    @api.onchange('account_id')
    def _onchange_account(self):
        if self.account_id:
            self.currency_id = self.account_id.currency_id

    @api.onchange('currency_rate', 'currency_id', 'amount_currency')
    def _onchange_currency_rate(self):
        if not ((self.debit and self.credit) or (not self.debit and not self.credit)) and self.currency_rate and not self.amount_currency:
            # if need calc amount_currency
            total_amount = self.debit if self.debit else -self.credit
            self.amount_currency = total_amount / self.currency_rate
        elif not ((self.debit and self.credit) or (not self.debit and not self.credit)) and not self.currency_rate and self.amount_currency:
            # need calc currency_rate
            total_amount = self.debit if self.debit else -self.credit
            self.currency_rate = abs(total_amount / self.amount_currency)
        elif not (self.debit or self.credit) and self.currency_rate and self.amount_currency:
            # need calc debit or credit
            total_amount = self.amount_currency * self.currency_rate
            self.debit = total_amount > 0 and total_amount or 0.0
            self.credit = total_amount < 0 and -total_amount or 0.0


class AccountFiscalyear(models.Model):
    _name = 'account.fiscalyear'
    _inherit = 'account.fiscalyear'

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, u'%s (%s)' % (record.name, record.company_id.name if record.company_id else '')))
        return result


class AccountPeriod(models.Model):
    _name = 'account.period'
    _inherit = 'account.period'

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, u'%s (%s)' % (record.name, record.company_id.name if record.company_id else '')))
        return result

    @api.v7
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


class AccountJournal(models.Model):
    _name = 'account.journal'
    _inherit = 'account.journal'

    @api.multi
    def name_get(self):
        """
        @return: Returns a list of tupples containing id, name
        """
        res = []
        for rs in self:
            if rs.currency:
                currency = rs.currency
            else:
                currency = rs.company_id.currency_id
            name = "%s (%s)%s" % (rs.name, currency.name, ('-%s' % rs.company_id.name) if rs.company_id else '')
            res += [(rs.id, name)]
        return res
