# data_manager.py

from models import Doctor, Cita


# === Diccionario principal ===
DOCTORES = {
    "ramirez": Doctor(
        id="ramirez",
        nombre="Dra. Ramírez",
        especialidad="Pediatría",
        citas=[
            Cita("lunes", "1:00"),
            Cita("lunes", "2:00", ocupada=True),
            Cita("miércoles", "2:00"),
        ],
    ),

    "gomez": Doctor(
        id="gomez",
        nombre="Dr. Gómez",
        especialidad="Cardiología",
        citas=[
            Cita("lunes", "2:00"),
            Cita("miércoles", "3:00", ocupada=True),
        ],
    ),

    "hernandez": Doctor(
        id="hernandez",
        nombre="Dr. Hernández",
        especialidad="Dermatología",
        citas=[
            Cita("lunes", "4:00"),
            Cita("miércoles", "2:00", ocupada=True),
        ],
    ),
}


# === Aliases o sinónimos válidos ===
ALIASES = {
    "dra ramirez": "ramirez",
    "dra. ramirez": "ramirez",
    "dr ramirez": "ramirez",
    "dr. ramirez": "ramirez",

    "dr gomez": "gomez",
    "dr. gomez": "gomez",

    "dr hernandez": "hernandez",
    "dr. hernandez": "hernandez",
}


# === Función principal ===
def get_doctor_info(nombre_doctor):
    if not nombre_doctor:
        return None

    nombre_doctor = nombre_doctor.lower()

    # 1) Buscar directo en el diccionario
    if nombre_doctor in DOCTORES:
        return DOCTORES[nombre_doctor]

    # 2) Buscar por alias
    if nombre_doctor in ALIASES:
        original = ALIASES[nombre_doctor]
        return DOCTORES.get(original)

    return None
