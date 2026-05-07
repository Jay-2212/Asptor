from dataclasses import dataclass


@dataclass(frozen=True)
class SourceConfig:
    name: str
    url: str


DEFAULT_SOURCES: tuple[SourceConfig, ...] = (
    SourceConfig(name="the_hindu_opinion", url="https://www.thehindu.com/opinion/"),
    SourceConfig(name="the_hindu_national", url="https://www.thehindu.com/news/national/"),
    SourceConfig(name="indian_express_explained", url="https://indianexpress.com/section/explained/"),
    SourceConfig(name="the_caravan", url="https://caravanmagazine.in/"),
    SourceConfig(name="fifty_two", url="https://fiftytwo.in/"),
)
