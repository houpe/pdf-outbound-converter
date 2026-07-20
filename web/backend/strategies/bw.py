from strategies import TemplateStrategy, register_strategy
from parsers.excel_parser_bw import parse_bw_excel

@register_strategy
class BwStrategy(TemplateStrategy):
    key = "bw"
    template_key = "bw"
    warehouse_code = "ZTOCSYH002"
    validate_split_codes = False
    
    def parse(self, path, filename=""):
        return parse_bw_excel(path)
