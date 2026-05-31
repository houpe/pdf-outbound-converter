from strategies import TemplateStrategy, register_strategy
from parsers.pdf_parser import extract_pdf_data


@register_strategy
class QzzStrategy(TemplateStrategy):
    key = "qzz"
    warehouse_code = "ZTOWHHY001"

    def parse(self, path: str, filename: str = ""):
        return extract_pdf_data(path)
