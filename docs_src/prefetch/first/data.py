user = await User.query.create(name="Saffier")

for i in range(5):
    await Post.query.create(comment="Comment number %s" % i, user=user)

for i in range(50):
    await Article.query.create(content="Comment number %s" % i, user=user)

esmerald = await User.query.create(name="Esmerald")

for i in range(15):
    await Post.query.create(comment="Comment number %s" % i, user=esmerald)

for i in range(20):
    await Article.query.create(content="Comment number %s" % i, user=esmerald)
