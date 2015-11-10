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

import time

from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import osv

from math import ceil

import logging

_logger = logging.getLogger(__name__)


class report_account_ledger(report_sxw.rml_parse):
    @staticmethod
    def _balance_closure():
        a = {
            'balance': 0.0,
            'balance_currency': 0.0,
            'balance_quantity': 0.0,
        }

        def init(values):
            a['balance'] = values[0]
            a['balance_currency'] = values[1]

        def push_line(line):
            a['balance'] += line.debit - line.credit
            a['balance_currency'] += line.amount_currency
            a['balance_quantity'] += line.quantity

        def result(value):
            return a[value]

        def clear():
            a['balance'] = 0.0
            a['balance_currency'] = 0.0
            a['balance_quantity'] = 0.0

        return init, result, push_line, clear

    @staticmethod
    def _data_closure():
        a = {
            'debit': 0.0,
            'debit_currency': 0.0,
            'debit_quantity': 0.0,
            'credit': 0.0,
            'credit_currency': 0.0,
            'credit_quantity': 0.0,
        }

        def push_line(line):
            if line.debit:
                a['debit'] += line.debit
                a['debit_currency'] += line.amount_currency
                a['debit_quantity'] += line.quantity
            if line.credit:
                a['credit'] += line.credit
                a['credit_currency'] += abs(line.amount_currency)
                a['credit_quantity'] += line.quantity
            return ''

        def get_balance():
            return a['debit'] - a['credit']

        def result(value):
            return a[value]

        def clear():
            a['debit'] = 0.0
            a['debit_currency'] = 0.0
            a['credit'] = 0.0
            a['credit_currency'] = 0.0
            a['debit_quantity'] = 0.0
            a['credit_quantity'] = 0.0

        return result, get_balance, push_line, clear

    def __init__(self, cr, uid, name, context=None):
        super(report_account_ledger, self).__init__(cr, uid, name, context=context)
        self.query = ""
        self.child_ids = ""
        self.sql_condition = " "
        self.tot_currency = 0.0
        self.period_sql = ""
        self.sold_accounts = {}
        daily_print, daily_balance, daily_push, daily_clear = self._data_closure()
        period_print, period_balance, period_push, period_clear = self._data_closure()
        year_print, year_balance, year_push, year_clear = self._data_closure()
        final_init, final_print, final_push, final_clear = self._balance_closure()
        self.localcontext.update({
            'time': time,
            'lines': self._get_lines,
            'balance': self._get_balance,
            'type': self._check_type,
            'period_date': self.get_date,
            'contrepartie': self._calc_contrepartie,
            'get_direction': self._get_direction,
            'account_name': self._get_account_name,
            'daily_print': daily_print,
            'daily_balance': daily_balance,
            'daily_push': daily_push,
            'daily_clear': daily_clear,
            'period_print': period_print,
            'period_balance': period_balance,
            'period_push': period_push,
            'period_clear': period_clear,
            'year_print': year_print,
            'year_balance': year_balance,
            'year_push': year_push,
            'year_clear': year_clear,
            'final_print': final_print,
            'final_push': final_push,
            'final_clear': final_clear,
            'final_init': final_init,
            'get_initial_balance': self._get_initial_balance,
        })
        self.context = context

    def _get_initial_balance(self, account_id):
        account_obj = self.pool.get('account.account')
        period_obj = self.pool.get('account.period')
        move_obj = self.pool.get('account.move')

        fiscalyear = self.pool.get('account.fiscalyear').browse(self.cr, self.uid, self.localcontext['fiscalyear_id'])
        account_child_ids = account_obj.search(self.cr, self.uid, [('parent_id', 'child_of', account_id)])
        debit = credit = balance = balance_currency = 0.0
        # 计算开账到期初前余额
        # if account user_type close_method is none(不结转)
        # if account user_type close method is balance(余额)
        # if account user_type close method is detail(全部结转)
        # if account user_type close method is unreconciled(未核销)
        # TODO:是否关账判断支持 if period_journal.period_id.state == 'done': sql:AND m.state IN %s
        period_open = [p.id for p in fiscalyear.period_ids if p.special][0]
        period_ids = period_obj.build_ctx_periods_in_company(self.cr, self.uid, period_open, self.localcontext['period_from_id'])
        period_ids.remove(self.localcontext['period_from_id'])

        ids_move = move_obj.search(self.cr, self.uid, [('period_id', 'in', period_ids)])
        if ids_move:
            self.cr.execute("""
              SELECT COALESCE(SUM(l.debit),0.0), COALESCE(SUM(l.credit),0.0), COALESCE(sum(debit-credit), 0.0), COALESCE(SUM(l.amount_currency),0.0)
              FROM account_move_line AS l, account_move AS m
              WHERE m.id = l.move_id AND m.id in %s AND l.account_id IN %s
            """, (tuple(ids_move), tuple(account_child_ids)))
            debit, credit, balance, balance_currency = self.cr.fetchall()[0]

        return balance, balance_currency

    def set_context(self, objects, data, ids, report_type=None):
        """
        设置 OE context
        """
        # set_context重载了rml_parse里面的set_context，会自动执行，data里的all_date在这里解析
        # self.borne_date = self.get_date(data['form'])
        self.product = ''
        self.partner = ''
        self.all_date = self.get_date(data)
        data['all_date'] = self.all_date
        self.sql_condition = self.get_threecolumns_ledger_type(data)
        self.localcontext['period_from_id'] = data['period_from'][0]
        self.localcontext['period_to_id'] = data['period_to'][0]
        self.localcontext['fiscalyear_id'] = data['fiscalyear'][0]
        self.localcontext['is_show_date'] = data.get('is_show_date', False)

        super(report_account_ledger, self).set_context(objects, data, ids, report_type)

    def _get_account_name(self, id):
        account_name = self.pool.get('account.account').name_get(self.cr, self.uid, [id], {})[0]
        # Account move print use Account here:
        return account_name[1]

    def get_date(self, data):
        """
        分析日期
        """
        period_obj = self.pool.get('account.period')
        period_start_obj = period_obj.browse(self.cr, self.uid, data["form"]['period_from'][0])
        period_end_obj = period_obj.browse(self.cr, self.uid, data["form"]['period_to'][0])
        fiscalyear_obj = self.pool.get('account.fiscalyear').browse(self.cr, self.uid, period_start_obj.fiscalyear_id.id)
        self.all_date = {
            'period_start_date_start': period_start_obj.date_start,
            'period_end_date_stop': period_end_obj.date_stop,
            'fiscalyear_obj_date_start': fiscalyear_obj.date_start,
        }
        return self.all_date

    def _get_periods(self):
        """
        获取期间
        """
        period_obj = self.pool.get('account.period')
        period_ids = period_obj.build_ctx_periods_in_company(self.cr, self.uid, self.localcontext['period_from_id'],
                                                             self.localcontext['period_to_id'])
        return period_obj.browse(self.cr, self.uid, period_ids)

    def _check_type(self, data):
        """
        检测报表类型
        """
        res = {}
        res['product'] = ""
        res['partner'] = ""
        res['report_name'] = u'三栏式明细账'
        account_obj = self.pool.get('account.account')
        if data.get('account_code', False):
            # add '00' for the old version l10n_cn
            accuont_ids = account_obj.search(self.cr, self.uid,
                                             ['|', ('code', '=', data['account_code']), ('code', '=', data['account_code'] + '00')])
            account = account_obj.browse(self.cr, self.uid, accuont_ids[0])
            res['report_name'] = account.name + u'日记账'
        elif data.get('product', False):
            res['report_name'] = u'产品'
            res['product'] = data['product'][1]
        elif data.get('partner', False):
            res['report_name'] = u'往来明细账'
            res['partner'] = data['partner'][1]
        return res

    def _calc_contrepartie(self, ids, context=None):
        """
        计算"对方科目"，下边这是法语吧
        """
        result = {}
        # for id in ids:
        #    result.setdefault(id, False)
        for account_line in self.pool.get('account.move.line').browse(self.cr, self.uid, ids, context):
            # For avoid long text in the field we will limit it to 5 lines
            result[account_line.id] = ' '
            num_id_move = str(account_line.move_id.id)
            num_id_line = str(account_line.id)
            account_id = str(account_line.account_id.id)
            # search the basic account
            # We have the account ID we will search all account move line from now until this time
            # We are in the case of we are on the top of the account move Line
            self.cr.execute('SELECT distinct(ac.code) as code_rest,ac.name as name_rest from account_account AS ac, account_move_line mv\
                    where ac.id = mv.account_id and mv.move_id = ' + num_id_move + ' and mv.account_id <> ' + account_id)
            res_mv = self.cr.dictfetchall()
            # we need a result more than 2 line to make the test so we will made the the on 1 because we have exclude the current line
            if (len(res_mv) >= 1):
                concat = ''
                rup_id = 0
                for move_rest in res_mv:
                    concat = concat + move_rest['code_rest'] + u' ' + move_rest['name_rest'] + '\n'
                    # result[account_line.id] = concat
                    if rup_id > 5:
                        # we need to stop the computing and to escape but before we will add "..."
                        # result[account_line.id] = concat + '...'
                        concat += '...'
                        break
                    rup_id += 1
                result[account_line.id] = concat
        return result

    def get_threecolumns_ledger_type(self, data):
        if data.get('product', False):
            self.sql_condition = " AND l.product_id ='" + str(data['product']) + "'"
            self.product = data['product']
        if data.get('partner', False):
            self.sql_condition = " AND l.partner_id ='" + str(data['partner']) + "'"
            self.partner = data['partner']
        return self.sql_condition

    def _get_lines(self, id, by_day=False, context=None):
        '''
        Get lines for threecolumns ledger
        '''
        result = []
        account_obj = self.pool.get('account.account')
        journal_obj = self.pool.get('account.journal')
        account_move_line_obj = self.pool.get('account.move.line')
        account_child_ids = account_obj.search(self.cr, self.uid, [('parent_id', 'child_of', id)])
        periods = self._get_periods()
        for period in periods:
            lines = []
            days = []
            all_days = []
            period_balance = 0
            journal_ids = journal_obj.search(self.cr, self.uid, [('type', '!=', 'situation')])
            account_move_line_ids = account_move_line_obj.search(self.cr, self.uid,
                                                                 [('account_id', 'in', account_child_ids), ('date', '<=', period.date_stop),
                                                                  ('date', '>=', period.date_start), ('state', '=', 'valid'),
                                                                  ('journal_id', 'in', journal_ids)], order='date,move_id')
            if self.partner:
                account_move_line_ids = account_move_line_obj.search(self.cr, self.uid,
                                                                     [('id', 'in', account_move_line_ids), ('partner_id', '=', self.partner[0])])
            if self.product:
                account_move_line_ids = account_move_line_obj.search(self.cr, self.uid,
                                                                     [('id', 'in', account_move_line_ids), ('product_id', '=', self.product[0])])
            for line in account_move_line_obj.browse(self.cr, self.uid, account_move_line_ids):
                lines.append(line)
                period_balance += line.debit - line.credit
                if by_day:
                    if line.date not in all_days:
                        day = {'lines': [], 'date': line.date}
                        all_days.append(line.date)
                        days.append(day)
                    days[all_days.index(line.date)]['lines'].append(line)

            if lines:
                result.append({
                    'period': period,
                    'lines': lines,
                    'period_balance': period_balance,
                    'days': days
                })
        return result

    def _get_balance(self, id, date_start=False, date_stop=False):
        '''
        return: quantity,amount_currency,debit,credit
        '''
        return self.pool.get('account.account').get_balance(self.cr, self.uid, id, date_start or False, date_stop or False, self.product or False,
                                                            self.partner or False)

    def _get_direction(self, balance):
        # FIXME: 这里估计是错的，还待研判
        str = ''
        if balance == 0:
            str = u'平'
        elif balance > 0:
            str = u'借'
        else:
            str = u'贷'
        return str


# 多个报表可以使用同一个解析器
class report_general_ledger(osv.AbstractModel):
    _name = 'report.oecn_account_print.report_general_ledger'
    _inherit = 'report.abstract_report'
    _template = 'oecn_account_print.report_general_ledger'
    _wrapped_report_class = report_account_ledger


class report_cash_journal(osv.AbstractModel):
    _name = 'report.oecn_account_print.report_cash_journal'
    _inherit = 'report.abstract_report'
    _template = 'oecn_account_print.report_cash_journal'
    _wrapped_report_class = report_account_ledger


class report_threecolumns_ledger(osv.AbstractModel):
    _name = 'report.oecn_account_print.report_threecolumns_ledger'
    _inherit = 'report.abstract_report'
    _template = 'oecn_account_print.report_threecolumns_ledger'
    _wrapped_report_class = report_account_ledger


class report_stock_ledger(osv.AbstractModel):
    _name = 'report.oecn_account_print.report_stock_ledger'
    _inherit = 'report.abstract_report'
    _template = 'oecn_account_print.report_stock_ledger'
    _wrapped_report_class = report_account_ledger


class report_currency_cash_journal(osv.AbstractModel):
    _name = 'report.oecn_account_print.report_currency_cash_journal'
    _inherit = 'report.abstract_report'
    _template = 'oecn_account_print.report_currency_cash_journal'
    _wrapped_report_class = report_account_ledger
