from strategies import TemplateStrategy, register_strategy
from parsers.excel_parser_hls import parse_hls_excel

@register_strategy
class HlsStrategy(TemplateStrategy):
    key = "hls"
    template_key = "hls"
    warehouse_code = "ZTOCSYH002"
    validate_split_codes = False
    
    def parse(self, path, filename=""):
        return parse_hls_excel(path)
