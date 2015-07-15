# -*- coding: utf-8 -*-
# author: cysnake4713
#
from openerp import tools
from openerp import models, fields, api
from openerp.tools.translate import _
import logging

_logger = logging.getLogger(__name__)


class DetailLedger(models.TransientModel):
    """
    Cash journal,Foreign currency journal,Stock ledger,Three columns ledger
    """
    _name = 'detail.ledger'
    _description = 'Detail Ledger(Cash journal, Foreign Currency journal, Stock Ledger, Three columns ledger)'

    account_id = fields.Many2one('account.account', 'Account', required=True, domain=[('type', '!=', 'view')])
    company_id = fields.Many2one('res.company', 'Company', required=True)
    period_from = fields.Many2one('account.period', 'Period From', required=True)
    period_to = fields.Many2one('account.period', 'Period To', required=True, domain=[('special', '=', False)])
    partner = fields.Many2one('res.partner', 'Partner')
    product = fields.Many2one('product.product', 'Product')

    _defaults = {
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.account', context=c),
    }

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            self.period_to = self.env['account.period'].with_context(account_period_prefer_normal=True, company_id=self.company_id.id).find()
            # get period form
            if self.period_to:
                fiscalyear_id = self.period_to.fiscalyear_id.id
                self.env.cr.execute(("SELECT date_start ,fiscalyear_id,id " \
                                     "FROM account_period " \
                                     "WHERE fiscalyear_id='%s'" \
                                     "ORDER BY date_start asc ") % (int(fiscalyear_id)))
                res = self.env.cr.dictfetchall()
                if res:
                    self.period_from = res[0]['id']

    @api.v7
    @api.cr_uid_ids_context
    def print_report(self, cr, uid, ids, context=None):
        """
        Check account type to know which format should be #print
        1. Account code start with '1001' or '1002', with currency, #print currency cash journal
        2. Account code start with '1001' or '1002', without currency, #print cash journal
        3. If user input product, #print stock ledger
        4. If user didn't input product, #print three columns ledger
        """
        datas = self.read(cr, uid, ids[0], ['account_id', 'period_from', 'period_to', 'product', 'partner', 'company_id'], context=context)

        datas['ids'] = [datas['account_id'][0]]
        account = self.pool.get('account.account').browse(cr, uid, datas['account_id'][0], context=context)
        if account.code[0:4] == '1001' or account.code[0:4] == '1002':
            datas['account_code'] = account.code[0:4]
            if account.currency_id:
                report_name = 'oecn_account_print.report_currency_cash_journal'
            else:
                report_name = 'oecn_account_print.report_cash_journal'
        elif datas.get('product', False):
            report_name = 'oecn_account_print.report_stock_ledger'
        else:
            report_name = 'oecn_account_print.report_threecolumns_ledger'
        datas['report_name'] = report_name
        # 数据必须放在datas[‘form’]中，因为几个报表使用的是同一个类里面的方法解析，必须保证格式统一
        datas.update({'form': datas.copy()})
        datas['form'].update({'ids': datas['ids']})
        # 返回的格式变了
        return self.pool['report'].get_action(cr, uid, ids, report_name, data=datas, context=context)


class GeneralLedger(models.TransientModel):
    """
    General Ledger
    """
    _name = 'general.ledger'
    _description = 'General Ledger'
    account_ids = fields.Many2many('account.account', 'general_ledger_account_account_rel', 'general_ledger_id', 'account_id', 'Account',
                                   required=True, domain=[('type', '!=', 'view')])
    company_id = fields.Many2one('res.company', 'Company', required=True)
    period_from = fields.Many2one('account.period', 'Period From', required=True)
    period_to = fields.Many2one('account.period', 'Period To', required=True, domain=[('special', '=', False)])

    @api.v7
    @api.cr_uid_ids_context
    def print_report(self, cr, uid, ids, context=None):
        res = self.read(cr, uid, ids[0], ['account_ids', 'company_id', 'period_from', 'period_to'])
        datas = {
            'ids': res['account_ids'],
            'model': 'account.account',
            'form': res,
        }
        datas.update(res)
        # datas = {'ids':res['account_ids'],'company_id':res['company_id'],'period_from':res['period_from'],'period_to':res['period_to']}
        datas['form']['ids'] = datas['ids']
        return self.pool['report'].get_action(cr, uid, ids, 'oecn_account_print.report_general_ledger', data=datas, context=context)

    _defaults = {
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'account.account', context=c),
    }

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            self.period_to = self.env['account.period'].with_context(account_period_prefer_normal=True, company_id=self.company_id.id).find()
            # get period form
            if self.period_to:
                fiscalyear_id = self.period_to.fiscalyear_id.id
                self.env.cr.execute(("SELECT date_start ,fiscalyear_id,id " \
                                     "FROM account_period " \
                                     "WHERE fiscalyear_id='%s'" \
                                     "ORDER BY date_start asc ") % (int(fiscalyear_id)))
                res = self.env.cr.dictfetchall()
                if res:
                    self.period_from = res[0]['id']
