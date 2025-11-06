DOCTORES = {
    "ramirez": {
        "especialidad": "pediatra", 
        "horario_atencion": "Lunes y Miércoles de 9:00 a 13:00"
    },
    "gomez": {
        "especialidad": "cardiologo", 
        "horario_atencion": "Martes y Jueves de 15:00 a 19:00"
    },
}

def get_doctor_info(nombre_doctor):
    if nombre_doctor:
        return DOCTORES.get(nombre_doctor.lower(), None)
    return None
