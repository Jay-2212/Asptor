from dataclasses import dataclass


@dataclass(frozen=True)
class SourceConfig:
    name: str
    url: str
    fallback_urls: tuple[str, ...] = ()


DEFAULT_SOURCES: tuple[SourceConfig, ...] = (
    SourceConfig(name="the_hindu_opinion", url="https://www.thehindu.com/opinion/"),
    SourceConfig(name="the_hindu_national", url="https://www.thehindu.com/news/national/"),
    SourceConfig(
        name="indian_express_explained",
        url="https://indianexpress.com/section/explained/",
        # Indian Express occasionally blocks GitHub-hosted runner IPs on the
        # HTML listing while leaving its public RSS feed available.
        fallback_urls=("https://indianexpress.com/section/explained/feed/",),
    ),
    SourceConfig(name="the_caravan", url="https://caravanmagazine.in/"),
    SourceConfig(name="fifty_two", url="https://fiftytwo.in/"),
)
