import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

import re

from django.conf import settings

from business_register.converter.business_converter import BusinessConverter
from business_register.models.company_models import (
    Assignee, BancruptcyReadjustment, Bylaw, Company, CompanyDetail, CompanyToKved,
    CompanyToPredecessor, CompanyType, ExchangeDataCompany, FounderFull, Predecessor,
    Signer, TerminationStarted
)
from data_ocean.converter import BulkCreateUpdateManager
from data_ocean.utils import cut_first_word, format_date_to_yymmdd, get_first_word


class CompanyConverter(BusinessConverter):

    def __init__(self):
        self.LOCAL_FILE_NAME = settings.LOCAL_FILE_NAME_UO
        self.LOCAL_FOLDER = settings.LOCAL_FOLDER
        self.CHUNK_SIZE = settings.CHUNK_SIZE_UO
        self.RECORD_TAG = 'SUBJECT'
        self.bulk_manager = BulkCreateUpdateManager(100000)
        self.branch_bulk_manager = BulkCreateUpdateManager(100000)
        self.all_companies_dict = self.put_all_objects_to_dict('hash_code', 'business_register',
                                                               'Company')
        self.all_bylaw_dict = self.put_all_objects_to_dict("name", "business_register", "Bylaw")
        self.all_company_type_dict = self.put_all_objects_to_dict('name', "business_register",
                                                                  "CompanyType")
        self.all_predecessors_dict = self.put_all_objects_to_dict("name", "business_register",
                                                                  "Predecessor")
        self.company_update_dict = {}
        self.company_create_dict = {}
        self.branch_to_parent = {}
        super().__init__()

    def save_or_get_company_type(self, type_from_record):
        company_type = type_from_record.lower()
        if company_type not in self.all_company_type_dict:
            company_type = CompanyType.objects.create(name=company_type)
            self.all_company_type_dict[company_type] = company_type
            return company_type
        else:
            return self.all_company_type_dict[company_type]

    def save_or_get_bylaw(self, bylaw_from_record):
        if bylaw_from_record not in self.all_bylaw_dict:
            bylaw = Bylaw.objects.create(name=bylaw_from_record)
            self.all_bylaw_dict[bylaw_from_record] = bylaw
            return bylaw
        else:
            return self.all_bylaw_dict[bylaw_from_record]

    def save_or_get_predecessor(self, item):
        if not item.xpath('NAME')[0].text in self.all_predecessors_dict:
            self.predecessor = Predecessor(
                name=item.xpath('NAME')[0].text.lower(),
                code=item.xpath('CODE')[0].text
            )
            self.predecessor.save()
            self.all_predecessors_dict[item.xpath('NAME')[0].text] = self.predecessor
            return self.predecessor
        else:
            self.predecessor = self.all_predecessors_dict[item.xpath('NAME')[0].text]
            return self.predecessor

    def initialize_company(self, name, short_name, company_type, edrpou, authorized_capital,
                           address, status, bylaw, registration_date, registration_info,
                           contact_info, authority, code):
        company = Company()
        company.name = name
        company.short_name = short_name
        company.company_type = company_type
        company.edrpou = edrpou
        company.authorized_capital = authorized_capital
        company.address = address
        company.status = status
        company.bylaw = bylaw
        company.registration_date = registration_date
        company.registration_info = registration_info
        company.contact_info = contact_info
        company.authority = authority
        company.hash_code = code
        return company

    def extract_founder_data(self, founder_info):
        info_to_list = founder_info.split(', ')
        # getting first element that is a name
        name = info_to_list[0]
        # checking if second element is a EDRPOU code
        edrpou = info_to_list[1] if self.find_edrpou(info_to_list[1]) else None
        # checking if other element is an EDRPOU code in case if the name has commas inside
        if not edrpou:
            for string in info_to_list:
                if self.find_edrpou(string):
                    edrpou = string
                    # getting the name with commas inside
                    info_to_new_list = founder_info.split(string)
                    name = info_to_new_list[0]
                    logger.info(f'name with a comma inside? See a founder with edrpou {edrpou}')
                    break
        equity = None
        element_with_equity = None
        for string in info_to_list:
            if string.startswith('розмір внеску до статутного фонду') and string.endswith('грн.'):
                element_with_equity = string
                equity = float(re.findall("\d+\.\d+", string)[0])
                break
        # deleting all info except the address
        address = founder_info.replace(name, '')
        if edrpou:
            address = address.replace(edrpou, '')
        if element_with_equity:
            address = address.replace(element_with_equity, '')
        if len(address) < 15:
            address = None
        return name, edrpou, address, equity

    def add_founders(self, founders_from_record, code):
        for item in founders_from_record:
            founder = FounderFull()
            # checking if there is additional data except name
            if ',' in item.text:
                name, founder.edrpou, founder.address, founder.equity = \
                    self.extract_founder_data(item.text)
                founder.name = name.lower()
            else:
                founder.name = item.text.lower()
            founder.hash_code = code
            self.bulk_manager.add_create(founder)

    # def branch_create(self, item, code):
    #     branch = Company()
    #     branch.name = item.xpath('NAME')[0].text
    #     branch.short_name = code
    #     branch.address = item.xpath('ADDRESS')[0].text
    #     if item.xpath('CREATE_DATE')[0].text:
    #         branch.registration_date = format_date_to_yymmdd(
    #             item.xpath('CREATE_DATE')[0].text
    #         ) or None
    #     branch.contact_info = item.xpath('CONTACTS')[0].text
    #     branch.authority = self.authority
    #     branch.bylaw = self.bylaw
    #     branch.company_type = self.company_type
    #     branch.status = self.status
    #     branch.hash_code = self.create_hash_code(branch.name, code)
    #     return branch

    def add_company_detail(self, founding_document_number, executive_power, superior_management,
                           managing_paper, terminated_info, termination_cancel_info, vp_dates,
                           code):
        company_detail = CompanyDetail()
        company_detail.founding_document_number = founding_document_number
        company_detail.executive_power = executive_power
        company_detail.superior_management = superior_management
        company_detail.managing_paper = managing_paper
        company_detail.terminated_info = terminated_info
        company_detail.termination_cancel_info = termination_cancel_info
        company_detail.vp_dates = vp_dates
        company_detail.hash_code = code
        self.bulk_manager.add_create(company_detail)

    def add_assignees(self, assignees_from_record, code):
        for item in assignees_from_record:
            assignee = Assignee()
            assignee.name = item.xpath('NAME')[0].text.lower()
            assignee.edrpou = item.xpath('CODE')[0].text
            assignee.hash_code = code
            self.bulk_manager.add_create(assignee)

    def add_bancruptcy_readjustment(self, record, code):
        bancruptcy_readjustment = BancruptcyReadjustment()
        if record.xpath('BANKRUPTCY_READJUSTMENT_INFO/OP_DATE'):
            bancruptcy_readjustment.op_date = format_date_to_yymmdd(
                record.xpath('BANKRUPTCY_READJUSTMENT_INFO/OP_DATE')[0].text) or None
            bancruptcy_readjustment.reason = record.xpath(
                'BANKRUPTCY_READJUSTMENT_INFO/REASON')[0].text.lower()
            bancruptcy_readjustment.sbj_state = record.xpath(
                'BANKRUPTCY_READJUSTMENT_INFO/SBJ_STATE')[0].text.lower()
            head_name = record.xpath(
                'BANKRUPTCY_READJUSTMENT_INFO/BANKRUPTCY_READJUSTMENT_HEAD_NAME')[0].text
            if head_name:
                bancruptcy_readjustment.head_name = head_name
            bancruptcy_readjustment.hash_code = code
            self.bulk_manager.add_create(bancruptcy_readjustment)

    def add_company_to_kved(self, kveds_from_record, code):
        for item in kveds_from_record:
            if not item.xpath('NAME'):
                continue
            kved_name = item.xpath('NAME')[0].text
            if not kved_name:
                continue
            company_to_kved = CompanyToKved()
            company_to_kved.kved = self.get_kved_from_DB(kved_name)
            company_to_kved.primary_kved = item.xpath('PRIMARY')[0].text == "так"
            company_to_kved.hash_code = code
            self.bulk_manager.add_create(company_to_kved)

    def add_company_to_kved_branch(self, kveds_from_record, code):
        for item in kveds_from_record:
            if not item.xpath('NAME'):
                continue
            kved_name = item.xpath('NAME')[0].text
            if not kved_name:
                continue
            company_to_kved = CompanyToKved()
            company_to_kved.kved = self.get_kved_from_DB(kved_name)
            company_to_kved.primary_kved = item.xpath('PRIMARY')[0].text == "так"
            company_to_kved.hash_code = code
            self.branch_bulk_manager.add_create(company_to_kved)

    def add_exchange_data(self, exchange_data, code):
        for item in exchange_data:
            if item.xpath('AUTHORITY_NAME'):
                exchange_answer = ExchangeDataCompany()
                exchange_answer.authority = self.save_or_get_authority(item.xpath(
                    'AUTHORITY_NAME')[0].text)
                taxpayer_type = item.xpath('TAX_PAYER_TYPE')[0].text
                if taxpayer_type:
                    exchange_answer.taxpayer_type = self.save_or_get_taxpayer_type(taxpayer_type)
                if item.xpath('START_DATE')[0].text:
                    exchange_answer.start_date = format_date_to_yymmdd(
                        item.xpath('START_DATE')[0].text) or None
                exchange_answer.start_number = item.xpath('START_NUM')[0].text
                if item.xpath('END_DATE')[0].text:
                    exchange_answer.end_date = format_date_to_yymmdd(
                        item.xpath('END_DATE')[0].text) or None
                exchange_answer.end_number = item.xpath('END_NUM')[0].text
                exchange_answer.hash_code = code
                self.bulk_manager.add_create(exchange_answer)

    def add_exchange_data_branch(self, exchange_data, name, code):
        if len(exchange_data) > 0:
            for item in exchange_data:
                exchange_answer = ExchangeDataCompany()
                if item.xpath('AUTHORITY_NAME'):
                    exchange_answer.authority = self.save_or_get_authority(
                        item.xpath('AUTHORITY_NAME')[0].text)
                    tax_payer_type = item.xpath('TAX_PAYER_TYPE')[0].text or Company.INVALID
                    exchange_answer.taxpayer_type = self.save_or_get_taxpayer_type(tax_payer_type)
                    if item.xpath('START_DATE')[0].text:
                        exchange_answer.start_date = format_date_to_yymmdd(
                            item.xpath('START_DATE')[0].text) or None
                    exchange_answer.start_number = item.xpath('START_NUM')[0].text
                    if item.xpath('END_DATE')[0].text:
                        exchange_answer.end_date = format_date_to_yymmdd(
                            item.xpath('END_DATE')[0].text) or None
                    exchange_answer.end_number = item.xpath('END_NUM')[0].text
                    exchange_answer.hash_code = self.create_hash_code(name, code)
                    self.branch_bulk_manager.add_create(exchange_answer)

    def add_company_to_predecessors(self, predecessors_from_record, code):
        for item in predecessors_from_record:
            if item.xpath('NAME'):
                company_to_predecessor = CompanyToPredecessor()
                company_to_predecessor.predecessor = self.save_or_get_predecessor(item)
                company_to_predecessor.hash_code = code
                self.bulk_manager.add_create(company_to_predecessor)

    def add_signers(self, signers_from_record, code):
        for item in signers_from_record:
            signer = Signer()
            signer.name = item.text.lower()
            signer.hash_code = code
            self.bulk_manager.add_create(signer)

    def add_termination_started(self, record, code):
        if record.xpath('TERMINATION_STARTED_INFO/OP_DATE'):
            termination_started = TerminationStarted()
            if record.xpath('TERMINATION_STARTED_INFO/OP_DATE')[0].text:
                termination_started.op_date = format_date_to_yymmdd(
                    record.xpath('TERMINATION_STARTED_INFO/OP_DATE')[0].text) or None
            termination_started.reason = record.xpath('TERMINATION_STARTED_INFO'
                                                      '/REASON')[0].text.lower()
            termination_started.sbj_state = record.xpath(
                'TERMINATION_STARTED_INFO/SBJ_STATE')[0].text.lower()
            signer_name = record.xpath('TERMINATION_STARTED_INFO/SIGNER_NAME')[0].text
            if signer_name:
                termination_started.signer_name = signer_name.lower()
            if record.xpath('TERMINATION_STARTED_INFO/CREDITOR_REQ_END_DATE')[0].text:
                termination_started.creditor_reg_end_date = format_date_to_yymmdd(
                    record.xpath('TERMINATION_STARTED_INFO/CREDITOR_REQ_END_DATE')[0].text) or '01.01.1990'
            termination_started.hash_code = code
            self.bulk_manager.add_create(termination_started)

    # def add_branches(self, record, edrpou):
    #     for item in record.xpath('BRANCHES')[0]:
    #         code = item.xpath('CODE')[0].text or Company.INVALID
    #         self.save_or_get_authority('EMP')
    #         self.save_or_get_bylaw('EMP')
    #         self.save_or_get_company_type('EMP')
    #         self.save_or_get_status('EMP')
    # try:
    #     branch = Company.objects.filter(
    #         hash_code=self.create_hash_code(item.xpath('NAME')[0].text, code)).first()
    # except:
    #     pass
    # if branch:
    #     branch.address = item.xpath('ADDRESS')[0].text
    #     if item.xpath('CREATE_DATE')[0].text:
    #         branch.registration_date = format_date_to_yymmdd(
    #             item.xpath('CREATE_DATE')[0].text) or None
    #     branch.contact_info = item.xpath('CONTACTS')[0].text
    #     self.branch_bulk_manager.add_update(branch)
    #     print('update')
    # else:
    #     branch = self.branch_create(item, code)
    #     self.branch_bulk_manager.add_create(branch)
    #     print('create')
    # branch = self.branch_create(item, code)
    # self.branch_bulk_manager.add_create(branch)
    # branch_kveds = item.xpath('ACTIVITY_KINDS')[0]
    # if len(branch_kveds):
    #     self.add_company_to_kved_branch(branch_kveds, item.xpath('NAME')[0].text, code)
    # self.add_exchange_data_branch(
    #     item.xpath('EXCHANGE_DATA')[0],
    #     item.xpath('NAME')[0].text, code
    # )
    # if item.xpath('SIGNER'):
    #     signer = Signer(
    #         name=item.xpath('SIGNER')[0].text,
    #         hash_code=self.create_hash_code(item.xpath('NAME')[0].text, code)
    #     )
    #     self.branch_bulk_manager.add_create(signer)
    # self.branch_to_parent[
    #     self.create_hash_code(item.xpath('NAME')[0].text, code)
    # ] = self.create_hash_code(record.xpath('NAME')[0].text, edrpou)

    def save_to_db(self, records):
        for record in records:
            name = record.xpath('NAME')[0].text.lower()
            short_name = record.xpath('SHORT_NAME')[0].text
            if short_name:
                short_name = short_name.lower()
            company_type = self.save_or_get_company_type(record.xpath('OPF')[0].text)
            edrpou = record.xpath('EDRPOU')[0].text or Company.INVALID
            code = name + edrpou
            address = record.xpath('ADDRESS')[0].text
            status = self.save_or_get_status(record.xpath('STAN')[0].text)
            founding_document_number = record.xpath('FOUNDING_DOCUMENT_NUM')[0].text
            executive_power = record.xpath('EXECUTIVE_POWER')[0].text
            if executive_power:
                executive_power = executive_power.lower()
            if len(record.xpath('FOUNDERS')[0]):
                self.add_founders(record.xpath('FOUNDERS')[0], code)
            if len(record.xpath('ACTIVITY_KINDS')[0]):
                self.add_company_to_kved(record.xpath('ACTIVITY_KINDS')[0], code)
            superior_management = record.xpath('SUPERIOR_MANAGEMENT')[0].text
            if superior_management:
                superior_management = superior_management.lower()
            if len(record.xpath('SIGNERS')[0]):
                self.add_signers(record.xpath('SIGNERS')[0], code)
            authorized_capital = record.xpath('AUTHORIZED_CAPITAL')[0].text
            if authorized_capital:
                authorized_capital = authorized_capital.replace(',', '.')
                authorized_capital = float(authorized_capital)
            bylaw = self.save_or_get_bylaw(record.xpath('STATUTE')[0].text)
            registration_date = None
            registration_info = None
            registration = record.xpath('REGISTRATION')[0].text
            if registration:
                registration_date = format_date_to_yymmdd(get_first_word(registration))
                registration_info = cut_first_word(registration)
            managing_paper = record.xpath('MANAGING_PAPER')[0].text
            if managing_paper:
                managing_paper = managing_paper.lower()
            # TODO: refactor branches storing
            # if len(record.xpath('BRANCHES')[0]):
            #     self.add_branches(record.xpath('BRANCHES')[0], code)
            if record.xpath('TERMINATION_STARTED_INFO/OP_DATE'):
                self.add_termination_started(record, code)
            if record.xpath('BANKRUPTCY_READJUSTMENT_INFO/OP_DATE'):
                self.add_bancruptcy_readjustment(record, code)
            if len(record.xpath('PREDECESSORS')[0]):
                self.add_company_to_predecessors(record.xpath('PREDECESSORS')[0], code)
            if len(record.xpath('ASSIGNEES')[0]):
                self.add_assignees(record.xpath('ASSIGNEES')[0], code)
            terminated_info = record.xpath('TERMINATED_INFO')[0].text
            if terminated_info:
                terminated_info = terminated_info.lower()
            termination_cancel_info = record.xpath('TERMINATION_CANCEL_INFO')[0].text
            if termination_cancel_info:
                termination_cancel_info = termination_cancel_info.lower()
            contact_info = record.xpath('CONTACTS')[0].text
            if record.xpath('EXCHANGE_DATA')[0]:
                self.add_exchange_data(record.xpath('EXCHANGE_DATA')[0], code)
            vp_dates = record.xpath('VP_DATES')[0].text
            authority = self.save_or_get_authority(record.xpath('CURRENT_AUTHORITY')[0].text)
            company = self.initialize_company(name, short_name, company_type, edrpou,
                                              authorized_capital, address, status, bylaw,
                                              registration_date, registration_info, contact_info,
                                              authority, code)
            self.add_company_detail(founding_document_number, executive_power, superior_management, managing_paper,
                                    terminated_info, termination_cancel_info, vp_dates, code)
            self.bulk_manager.add_create(company)
        # if len(self.bulk_manager._update_queues['business_register.Company']):
        #     self.bulk_manager._commit_update(Company, ['name', 'short_name', 'company_type', 'edrpou'])
        self.bulk_manager._commit_create(Company)
        company_update_dict = {}
        company_create_dict = {}

        for company in self.bulk_manager._update_queues['business_register.Company']:
            company_update_dict[company.hash_code] = company
        for company in self.bulk_manager._create_queues['business_register.Company']:
            company_create_dict[company.hash_code] = company

        self.bulk_manager._update_queues['business_register.Company'] = []
        self.bulk_manager._create_queues['business_register.Company'] = []

        # for branch in self.branch_bulk_manager._create_queues['business_register.Company']:
        #     if self.branch_to_parent[branch.hash_code] in company_update_dict:
        #         branch.parent = company_update_dict[self.branch_to_parent[branch.hash_code]]
        #     else:
        #         branch.parent = company_create_dict[self.branch_to_parent[branch.hash_code]]
        #
        # for branch in self.branch_bulk_manager._update_queues['business_register.Company']:
        #     if self.branch_to_parent[branch.hash_code] in company_update_dict:
        #         branch.parent = company_update_dict[self.branch_to_parent[branch.hash_code]]
        #     else:
        #         branch.parent = company_create_dict[self.branch_to_parent[branch.hash_code]]
        #
        # branch_to_parent = {}

        for assignee in self.bulk_manager._create_queues['business_register.Assignee']:
            if assignee.hash_code in company_update_dict:
                assignee.company = company_update_dict[assignee.hash_code]
            else:
                assignee.company = company_create_dict[assignee.hash_code]

        for company_to_kved in self.bulk_manager._create_queues['business_register.CompanyToKved']:
            if company_to_kved.hash_code in company_update_dict:
                company_to_kved.company = company_update_dict[company_to_kved.hash_code]
            else:
                company_to_kved.company = company_create_dict[company_to_kved.hash_code]

        for exchange_data in self.bulk_manager._create_queues['business_register.ExchangeDataCompany']:
            if exchange_data.hash_code in company_update_dict:
                exchange_data.company = company_update_dict[exchange_data.hash_code]
            else:
                exchange_data.company = company_create_dict[exchange_data.hash_code]

        for founder in self.bulk_manager._create_queues['business_register.FounderFull']:
            if founder.hash_code in company_update_dict:
                founder.company = company_update_dict[founder.hash_code]
            else:
                founder.company = company_create_dict[founder.hash_code]

        for bancruptcy_readjustment in self.bulk_manager._create_queues['business_register.BancruptcyReadjustment']:
            if bancruptcy_readjustment.hash_code in company_update_dict:
                bancruptcy_readjustment.company = company_update_dict[bancruptcy_readjustment.hash_code]
            else:
                bancruptcy_readjustment.company = company_create_dict[bancruptcy_readjustment.hash_code]

        for company_detail in self.bulk_manager._create_queues['business_register.CompanyDetail']:
            if company_detail.hash_code in company_update_dict:
                company_detail.company = company_update_dict[company_detail.hash_code]
            else:
                company_detail.company = company_create_dict[company_detail.hash_code]

        for company_to_predecessor in self.bulk_manager._create_queues['business_register.CompanyToPredecessor']:
            if company_to_predecessor.hash_code in company_update_dict:
                company_to_predecessor.company = company_update_dict[company_to_predecessor.hash_code]
            else:
                company_to_predecessor.company = company_create_dict[company_to_predecessor.hash_code]

        for signer in self.bulk_manager._create_queues['business_register.Signer']:
            if signer.hash_code in company_update_dict:
                signer.company = company_update_dict[signer.hash_code]
            else:
                signer.company = company_create_dict[signer.hash_code]

        for termination_started in self.bulk_manager._create_queues['business_register.TerminationStarted']:
            if termination_started.hash_code in company_update_dict:
                termination_started.company = company_update_dict[termination_started.hash_code]
            else:
                termination_started.company = company_create_dict[termination_started.hash_code]

        self.bulk_manager._commit_create(Assignee)
        self.bulk_manager._commit_create(FounderFull)
        self.bulk_manager._commit_create(BancruptcyReadjustment)
        self.bulk_manager._commit_create(CompanyDetail)
        self.bulk_manager._commit_create(CompanyToKved)
        self.bulk_manager._commit_create(ExchangeDataCompany)
        self.bulk_manager._commit_create(CompanyToPredecessor)
        self.bulk_manager._commit_create(Signer)
        self.bulk_manager._commit_create(TerminationStarted)
        if len(self.branch_bulk_manager._update_queues['business_register.Company']) > 0:
            self.branch_bulk_manager._commit_update(Company, ['name', 'short_name'])
        self.branch_bulk_manager._commit_create(Company)

        company_update_dict = {}
        company_create_dict = {}

        for company in self.branch_bulk_manager._update_queues['business_register.Company']:
            company_update_dict[company.hash_code] = company
        for company in self.branch_bulk_manager._create_queues['business_register.Company']:
            company_create_dict[company.hash_code] = company

        self.bulk_manager._create_queues['business_register.Assignee'] = []
        self.bulk_manager._create_queues['business_register.FounderFull'] = []
        self.bulk_manager._create_queues['business_register.BancruptcyReadjustment'] = []
        self.bulk_manager._create_queues['business_register.CompanyDetail'] = []
        self.bulk_manager._create_queues['business_register.CompanyToKved'] = []
        self.bulk_manager._create_queues['business_register.ExchangeDataCompany'] = []
        self.bulk_manager._create_queues['business_register.CompanyToPredecessor'] = []
        self.bulk_manager._create_queues['business_register.Signer'] = []
        self.bulk_manager._create_queues['business_register.TerminationStarted'] = []
        self.branch_bulk_manager._update_queues['business_register.Company'] = []
        self.branch_bulk_manager._create_queues['business_register.Company'] = []

        for company_to_kved in self.branch_bulk_manager._create_queues['business_register.CompanyToKved']:
            if company_to_kved.hash_code in company_update_dict:
                company_to_kved.company = company_update_dict[company_to_kved.hash_code]
            else:
                company_to_kved.company = company_create_dict[company_to_kved.hash_code]

        for exchange_data in self.branch_bulk_manager._create_queues['business_register.ExchangeDataCompany']:
            if exchange_data.hash_code in company_update_dict:
                exchange_data.company = company_update_dict[exchange_data.hash_code]
            else:
                exchange_data.company = company_create_dict[exchange_data.hash_code]

        for signer in self.branch_bulk_manager._create_queues['business_register.Signer']:
            if signer.hash_code in company_update_dict:
                signer.company = company_update_dict[signer.hash_code]
            else:
                signer.company = company_create_dict[signer.hash_code]

        self.branch_bulk_manager._commit_create(CompanyToKved)
        self.branch_bulk_manager._commit_create(ExchangeDataCompany)
        self.branch_bulk_manager._commit_create(Signer)
        self.branch_bulk_manager._create_queues['business_register.CompanyToKved'] = []
        self.branch_bulk_manager._create_queues['business_register.ExchangeDataCompany'] = []
        self.branch_bulk_manager._create_queues['business_register.Signer'] = []