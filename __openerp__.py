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
# __author__ = hdjmd@qq.com

{
    "name": "符合中国会计习惯的财务功能",
    "version": "8.0",
    "description": '''
    中国财务报表打印模块
    增加视图：
        中国凭证
    增加报表
        总账
        现金日记账
        外币日记账
        往来明细账

    In china, all account documents need to be printed and keep for internal
    or external audit. So this module will print following account documnets
    with china standard format:
    Account moves

    General ledger (accouts move history)
    Cash journal (for cash and bank accounts)
    Detail ledger  (accounts move histoy group by partner or product)

        Three columns ledger
        Stock ledger
        Cash journal
        Foreign currency cash journal

    todo:
    Balance Sheet
    Profit and Loss Sheet
    Cash Flow Statement

    Further more, we hide the concept "Journal" for chinese accountant never
    use this concept. They care more about move number and move number must
    be organized in a period
    ''',
    "author": "开阖软件,cysnake4713@gmail.com,hdjmd@qq.com",
    "website": "http://www.osbzr.com",
    "depends": ["account", "account_accountant", "l10n_cn"],
    "data": [

        "data/account.financial.report.csv",

        "security/oecn_account_print_security.xml",
        "security/ir.model.access.csv",

        "wizard/oecn_account_print_wizard_view.xml",
        "views/oecn_account_print_view.xml",
        "views/oecn_account_print_report.xml",
        "views/menuitem.xml",

        "report/report_account_move.xml",
        'report/report_general_ledger.xml',
        "report/report_cash_journal.xml",
        "report/report_threecolumns_ledger.xml",
        "report/report_stock_ledger.xml",
        "report/report_currency_cash_journal.xml",

        "report/report_financial_pal.xml",
        "report/report_financial_aab.xml",
    ],
    "installable": True,
    "certificate": "",
    "category": "Accounting & Finance",
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
