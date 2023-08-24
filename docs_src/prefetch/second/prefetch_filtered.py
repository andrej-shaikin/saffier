import saffier
from saffier import Prefetch

database = saffier.Database("sqlite:///db.sqlite")
models = saffier.Registry(database=database)

# All the tracks that belong to a specific `Company`.
# The tracks are associated with `albums` and `studios`
# where the `Track` will be also internally filtered
company = await Company.query.prefetch_related(
    Prefetch(
        related_name="companies__studios__tracks",
        to_attr="tracks",
        queryset=Track.query.filter(title__icontains="bird"),
    )
)
