"""Fixed lists for the Crop Advice and profile forms. Keys map to translations (cp.*, stage.*, soil.*, wat.*, tp.*);
English labels are what the AI model receives."""

CROPS = {"paddy": "Paddy (rice)", "wheat": "Wheat", "cotton": "Cotton", "sugarcane": "Sugarcane",
         "groundnut": "Groundnut", "maize": "Maize", "tomato": "Tomato", "chilli": "Chilli", "banana": "Banana",
         "other": "Other crop"}
STAGES = {"prep": "land preparation / not sown yet", "nursery": "nursery / seedling stage",
          "vegetative": "vegetative growth (leaves and stems)", "flowering": "flowering",
          "fruiting": "fruit / grain formation", "maturity": "mature, close to harvest", "harvest": "after harvest"}
SOILS = {"unknown": "", "red": "red soil", "black": "black cotton soil", "alluvial": "alluvial soil",
         "sandy": "sandy soil", "clay": "clay soil", "loamy": "loamy soil"}
WATER = {"rainfed": "rainfed (rain only)", "canal": "canal irrigation", "borewell": "bore well / tube well",
         "drip": "drip or sprinkler", "tank": "tank / pond", "mixed": "mixed or other"}
TOPICS = ["general", "irrigation", "fertilizer", "pest", "season"]

STATES = ["Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana",
          "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
          "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
          "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands", "Chandigarh",
          "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep",
          "Puducherry"]
