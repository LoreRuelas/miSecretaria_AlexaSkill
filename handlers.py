# data_manager.py
import unicodedata

DOCTORES = {
    "ramirez": {
        "nombre": "Dra. Ramírez",
        "especialidad": "Pediatría",
        "dias": ["monday", "wednesday"],  # ISO weekday names for comparison
        "inicio": 9,   # hora inicio (inclusive) -> 9 = 09:00
        "fin": 13,     # hora fin (exclusive) -> 13 = hasta 13:00 (última franja 12:00-13:00)
    },
    "gomez": {
        "nombre": "Dr. Gómez",
        "especialidad": "Cardiología",
        "dias": ["tuesday", "thursday"],
        "inicio": 15,
        "fin": 19,     # 15..18 -> franjas 15-16,16-17,17-18,18-19
    },
    "hernandez": {
        "nombre": "Dr. Hernández",
        "especialidad": "Dermatología",
        "dias": ["friday"],
        "inicio": 10,
        "fin": 14,
    },
}

# Usuarios y citas en memoria
# USUARIOS: key = user_key (nombre normalizado o telefono), value = {"nombre":..., "telefono":...}
USUARIOS = {}

# CITAS: key = usuario_key, value = {"doctor": "ramirez", "fecha": "YYYY-MM-DD", "hora": "HH:MM"}
CITAS = {}

def _strip_accents(text: str) -> str:
    if not text:
        return text
    text = unicodedata.normalize("NFKD", text)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    return text

def normalize_name(name: str) -> str:
    if not name:
        return None
    n = _strip_accents(name).lower().strip()
    # eliminar prefijos comunes
    n = n.replace("dr ", "").replace("dra ", "").replace("doctor ", "").replace("doctora ", "")
    return n

def register_user(nombre: str, telefono: str = None) -> str:
    key = normalize_name(nombre) if nombre else None
    if not key and telefono:
        key = f"tel_{telefono}"
    if not key:
        return None
    USUARIOS[key] = {"nombre": nombre, "telefono": telefono}
    return key

def find_user_by_name_or_phone(text: str) -> str:
    """
    Dado nombre o teléfono (texto), intenta encontrar la key del usuario.
    """
    if not text:
        return None
    # si parece número
    clean = text.strip()
    if clean.isdigit():
        # buscar por telefono
        for k, v in USUARIOS.items():
            if v.get("telefono") and clean in v.get("telefono"):
                return k
        return None
    # buscar por nombre normalizado
    candidate = normalize_name(clean)
    if candidate in USUARIOS:
        return candidate
    # buscar por coincidencia parcial
    for k, v in USUARIOS.items():
        if candidate in normalize_name(v.get("nombre", "")):
            return k
    return None

def get_doctor_info(nombre_doctor: str):
    if not nombre_doctor:
        return None
    key = normalize_name(nombre_doctor)
    return DOCTORES.get(key)

def _weekday_from_date(date_iso: str) -> str:
    """
    date_iso expected YYYY-MM-DD
    returns lowercase english weekday like 'monday'
    """
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(date_iso)
        return dt.strftime("%A").lower()
    except Exception:
        return None

def get_available_slots(doctor_key: str, fecha_iso: str):
    """
    Devuelve lista de horas disponibles en formato "HH:MM" para el doctor en la fecha.
    Genera intervalos de 1 hora según inicio/fin definidos y excluye horas ya ocupadas.
    """
    doctor = DOCTORES.get(doctor_key)
    if not doctor:
        return []

    weekday = _weekday_from_date(fecha_iso)
    if weekday not in doctor["dias"]:
        return []

    inicio = doctor["inicio"]
    fin = doctor["fin"]
    slots = [f"{h:02d}:00" for h in range(inicio, fin)]
    # quitar los slots ocupados
    ocupados = []
    for u, cita in CITAS.items():
        if cita.get("doctor") == doctor_key and cita.get("fecha") == fecha_iso:
            ocupados.append(cita.get("hora"))
    disponibles = [s for s in slots if s not in ocupados]
    return disponibles

def user_has_appointment(user_key: str) -> bool:
    return user_key in CITAS

def save_appointment(user_key: str, doctor_key: str, fecha_iso: str, hora_str: str) -> bool:
    # verifica disponibilidad
    disponibles = get_available_slots(doctor_key, fecha_iso)
    if hora_str not in disponibles:
        return False
    CITAS[user_key] = {"doctor": doctor_key, "fecha": fecha_iso, "hora": hora_str}
    return True

def get_user_appointment(user_key: str):
    return CITAS.get(user_key)

def cancel_appointment(user_key: str) -> bool:
    if user_key in CITAS:
        del CITAS[user_key]
        return True
    return False

def move_appointment(user_key: str, nueva_fecha: str, nueva_hora: str) -> bool:
    cita = CITAS.get(user_key)
    if not cita:
        return False
    doctor = cita.get("doctor")
    disponibles = get_available_slots(doctor, nueva_fecha)
    if nueva_hora not in disponibles:
        return False
    # actualizar
    CITAS[user_key] = {"doctor": doctor, "fecha": nueva_fecha, "hora": nueva_hora}
    return True
