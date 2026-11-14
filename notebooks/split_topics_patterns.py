import re
AGRI = re.compile(r"\bagricultur\w*|\bfarm(?:s|er|ers|ing)?\b|\bcrops?\b|\bharvests?\b|\bfertili[sz]\w*|\blivestock\b|\bcattle\b|\bcommon agricultural policy\b|\bfisher\w*", re.I)
FOOD = re.compile(r"\bfood\b|\bfoods\b|\bnutrition\w*|\bhunger\b|\bdiets?\b|\bgrocer\w*|\bsupermarkets?\b|\bfood security\b", re.I)
