"""Plantillas principales."""

FEED_TEMPLATE = """<!DOCTYPE html><html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nexus</title>
</head>
<body>
<div class="page">
  <h1>Feed</h1>
  {% for post in posts %}
  <div class="post">{{ post.content }}</div>
  {% endfor %}
</div>
</body></html>"""
