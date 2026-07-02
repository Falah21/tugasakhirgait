def calculate_bmi(weight_kg, height_cm):
    if height_cm > 0:
        height_m = height_cm / 100
        return weight_kg / (height_m ** 2)
    return 0

def classify_bmi(bmi):
    if bmi < 17.0:
        return "Kurus Berat"
    elif bmi < 18.5:
        return "Kurus Ringan"
    elif bmi < 25.1:
        return "Normal"
    elif bmi < 27.1:
        return "Gemuk Ringan"
    else:
        return "Gemuk Berat"
