import saffier

# Create some records

await User.query.create(name="Adam", email="adam@saffier.dev")
await User.query.create(name="Eve", email="eve@saffier.dev")

# Query using the and_
await User.query.filter(saffier.and_(User.columns.name == "Adam")).filter(
    saffier.and_(User.columns.email == "adam@saffier.dev")
)
