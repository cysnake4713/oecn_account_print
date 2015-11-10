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

from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp import tools
import openerp.addons.decimal_precision as dp

import logging

_logger = logging.getLogger(__name__)


class account_account(osv.osv):
    _inherit = 'account.account'

    def get_balance(self, cr, uid, ids, date_start=False, date_stop=False, product=False, partner=False):
        '''
        Get the balance from date_start to date_stop,fielter by product or partner
        '''
        result = {
            'debit': 0.0,
            'debit_quantity': 0.0,
            'debit_amount_currency': 0.0,
            'credit': 0.0,
            'credit_quantity': 0.0,
            'credit_amount_currency': 0.0,
            'balance': 0.0,
            'amount_currency': 0.0,
            'quantity': 0.0,
        }
        account_move_line_obj = self.pool.get('account.move.line')
        journal_obj = self.pool.get('account.journal')
        account_obj = self.pool.get('account.account')

        journal_ids = journal_obj.search(cr, uid, [('type', '!=', 'situation')])
        account_ids = account_obj.search(cr, uid, [('parent_id', 'child_of', ids)])
        search_condition = [('account_id', 'in', account_ids), ('state', '=', 'valid'), ('journal_id', 'in', journal_ids)]
        if date_start:
            search_condition.append(('date', '>=', date_start))
        if date_stop:
            search_condition.append(('date', '<=', date_stop))
        if product:
            search_condition.append(('product_id', '=', product[0]))
        if partner:
            search_condition.append(('partner_id', '=', partner[0]))

        line_ids = account_move_line_obj.search(cr, uid, search_condition)
        lines = account_move_line_obj.browse(cr, uid, line_ids)
        for line in lines:
            if line.debit > 0:
                result['debit_quantity'] += line.quantity or 0
                result['debit_amount_currency'] += line.amount_currency or 0
            else:
                result['credit_quantity'] += line.quantity or 0
                result['credit_amount_currency'] += abs(line.amount_currency) or 0
            result['balance'] += line.debit - line.credit
            result['quantity'] = result['debit_quantity'] - result['credit_quantity']
            result['amount_currency'] = result['debit_amount_currency'] - result['credit_amount_currency']
            result['debit'] += line.debit or 0
            result['credit'] += line.credit or 0

        return result


class account_periodly(osv.osv):
    _name = "account.periodly"
    _description = "科目余额表"
    _auto = False

    def _compute_balances(self, cr, uid, ids, field_names, arg=None, context=None,
                          query='', query_params=()):
        all_periodly_lines = self.search(cr, uid, [], context=context)
        all_companies = self.pool.get('res.company').search(cr, uid, [], context=context)
        all_accounts = self.pool.get('account.account').search(cr, uid, [], context=context)
        current_sum = dict((company, dict((account, 0.0) for account in all_accounts)) for company in all_companies)
        res = dict((id, dict((fn, 0.0) for fn in field_names)) for id in all_periodly_lines)
        for record in self.browse(cr, uid, all_periodly_lines, context=context):
            res[record.id]['starting_balance'] = current_sum[record.company_id.id][record.account_id.id]
            current_sum[record.company_id.id][record.account_id.id] += record.balance
            res[record.id]['ending_balance'] = current_sum[record.company_id.id][record.account_id.id]
        return res

    _columns = {
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscalyear', readonly=True),
        'period_id': fields.many2one('account.period', 'Period', readonly=True),
        'account_id': fields.many2one('account.account', 'Account', readonly=True),
        'debit': fields.float('Debit', readonly=True),
        'credit': fields.float('Credit', readonly=True),
        'balance': fields.float('Balance', readonly=True),
        'date': fields.date('Beginning of Period Date', readonly=True),
        'starting_balance': fields.function(_compute_balances, digits_compute=dp.get_precision('Account'), string='Starting Balance',
                                            multi='balance'),
        'ending_balance': fields.function(_compute_balances, digits_compute=dp.get_precision('Account'), string='Ending Balance', multi='balance'),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
    }

    _order = 'date asc,account_id,company_id'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_periodly')
        # 感谢 hdjmd <hdjmd@qq.com> 提供科目余额表的sql优化~
        cr.execute("""
CREATE OR REPLACE VIEW account_periodly AS (
  SELECT
    t.fiscalyear_id,
    period_id,
    account_id,
    debit,
    credit,
    balance,
    date,
    t.company_id,
    t.id
  FROM
    (SELECT
       fiscalyear_id,
       period_id,
       account_id,
       debit,
       credit,
       balance,
       date,
       company_id,
       row_number()
       OVER (
         ORDER BY period_id, account_id, company_id) AS id
     FROM
       (SELECT
          fiscalyear_id           fiscalyear_id,
          period_id               period_id,
          account_id              account_id,
          sum(a.debit)            debit,
          sum(a.credit)           credit,
          sum(a.debit - a.credit) balance,
          date                    date,
          company_id              company_id
        FROM
          (
            SELECT
              b.fiscalyear_id         AS fiscalyear_id,
              b.id                    AS period_id,
              a.account_id            AS account_id,
              sum(a.debit)            AS debit,
              sum(a.credit)           AS credit,
              sum(a.debit - a.credit) AS balance,
              b.date_start            AS date,
              a.company_id            AS company_id
            FROM
              account_move_line a
              LEFT JOIN account_period b
                ON a.period_id = b.id AND a.company_id = b.company_id
            WHERE a.state != 'draft' AND b.special = FALSE
            GROUP BY
              b.fiscalyear_id,
              b.id,
              a.account_id,
              b.date_start,
              a.company_id
            UNION ALL
            SELECT
              DISTINCT
              b.fiscalyear_id fiscalyear_id,
              a.period_id     period_id,
              a.account_id    account_id,
              0               debit,
              0               credit,
              0               balance,
              b.date_start    date,
              a.company_id    company_id
            FROM
              (
                SELECT
                  DISTINCT
                  b.account_id,
                  b.company_id,
                  a.period_id
                FROM account_move_line a
                  LEFT JOIN
                  (SELECT DISTINCT
                     account_id,
                     company_id,
                     period_id
                   FROM account_move_line
                  ) b
                    ON a.company_id = b.company_id
                WHERE a.period_id > b.period_id
              ) a LEFT JOIN
              account_period b
                ON a.period_id = b.id AND a.company_id = b.company_id
          ) a
        GROUP BY
          fiscalyear_id,
          period_id,
          account_id,
          date,
          company_id
       ) a
    ) t
    LEFT JOIN account_period ap
      ON t.period_id = ap.id
  WHERE ap.special = FALSE
)

        """)
