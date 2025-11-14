# data_manager.py
# Lógica de datos en memoria para la skill "Secretaria Personal"
import unicodedata
from datetime import datetime, timedelta

DIAS_ENG_TO_ESP = {
    "monday": "lunes",
    "tuesday": "martes",
    "wednesday": "miércoles",
    "thursday": "jueves",
    "friday": "viernes",
    "saturday": "sábado",
    "sunday": "domingo"
}

DIAS_ESP_TO_INDEX = {
    "lunes": 0,
    "martes": 1,
    "miércoles": 2,
    "miercoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sábado": 5,
    "sabado": 5,
    "domingo": 6
}

# Doctores: dias en español para respuestas y validación
DOCTORES = {
    "ramirez": {
        "nombre": "Dra. Ramírez",
        "especialidad": "Pediatría",
        "dias": ["lunes", "miércoles"],
        "inicio": 9,   # 09:00
        "fin": 13      # hasta 13:00 (última franja 12:00)
    },
    "gomez": {
        "nombre": "Dr. Gómez",
        "especialidad": "Cardiología",
        "dias": ["martes", "jueves"],
        "inicio": 15,  # 15:00
        "fin": 19      # hasta 19:00 (última franja 18:00)
    },
    "hernandez": {
        "nombre": "Dr. Hernández",
        "especialidad": "Dermatología",
        "dias": ["viernes"],
        "inicio": 10,
        "fin": 14
    },
}

USUARIOS = {}   # key -> {"nombre":..., "telefono":...}
CITAS = {}      # key -> {"doctor": "ramirez", "fecha": "YYYY-MM-DD", "hora": "HH:MM"}

# -----------------------
# Normalización
# -----------------------
def _strip_accents(text: str) -> str:
    if not text:
        return text
    text = unicodedata.normalize("NFKD", text)
    return "".join([c for c in text if not unicodedata.combining(c)])

def normalize_name(name: str) -> str:
    if not name:
        return None
    n = _strip_accents(name).lower().strip()
    for prefix in ("doctor ", "doctora ", "dr ", "dra ", "dr. ", "dra. "):
        if n.startswith(prefix):
            n = n.replace(prefix, "").strip()
    n = " ".join(n.split())
    return n

# -----------------------
# Usuarios
# -----------------------
def register_user(nombre: str, telefono: str) -> str:
    if not nombre or not telefono:
        return None
    key = normalize_name(nombre) if nombre else f"tel_{telefono}"
    USUARIOS[key] = {"nombre": nombre, "telefono": telefono}
    return key

def find_user_by_name_or_phone(text: str) -> str:
    if not text:
        return None
    clean = text.strip()
    digits = "".join([c for c in clean if c.isdigit()])
    if digits:
        for k, v in USUARIOS.items():
            tel = v.get("telefono") or ""
            if digits in "".join([c for c in tel if c.isdigit()]):
                return k
    cand = normalize_name(clean)
    if cand in USUARIOS:
        return cand
    for k, v in USUARIOS.items():
        if cand in normalize_name(v.get("nombre", "")):
            return k
    return None

# -----------------------
# Doctor info / disponibilidad
# -----------------------
def get_doctor_info(nombre_doctor: str):
    if not nombre_doctor:
        return None
    key = normalize_name(nombre_doctor)
    if key in DOCTORES:
        info = DOCTORES[key]
        return {
            "key": key,
            "nombre": info["nombre"],
            "especialidad": info["especialidad"],
            "dias": info["dias"],
            "inicio": info["inicio"],
            "fin": info["fin"]
        }
    return None

def _weekday_index_from_iso(date_iso: str):
    try:
        dt = datetime.fromisoformat(date_iso)
        return dt.weekday()  # 0=Monday
    except Exception:
        return None

def _next_date_for_weekday(start_date: datetime, weekday_index: int) -> datetime:
    days_ahead = weekday_index - start_date.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return start_date + timedelta(days=days_ahead)

def day_name_to_next_iso(day_name: str, reference: datetime = None) -> str:
    """
    Convierte 'martes' -> próxima fecha ISO 'YYYY-MM-DD' que sea martes.
    Si day_name es en inglés se intenta mapear.
    """
    if not reference:
        reference = datetime.now()
    if not day_name:
        return None
    d = day_name.strip().lower()
    # aceptar dias en inglés (Alexa a veces devuelve en inglés)
    if d in DIAS_ESP_TO_INDEX:
        idx = DIAS_ESP_TO_INDEX[d]
    else:
        # si vino en inglés convertir
        eng = d.lower()
        esp = DIAS_ENG_TO_ESP.get(eng)
        if esp and esp in DIAS_ESP_TO_INDEX:
            idx = DIAS_ESP_TO_INDEX[esp]
        else:
            return None
    next_dt = _next_date_for_weekday(reference, idx)
    return next_dt.date().isoformat()

def get_available_slots(doctor_key: str, fecha_iso: str):
    if not doctor_key or not fecha_iso:
        return []
    k = normalize_name(doctor_key)
    doc = DOCTORES.get(k)
    if not doc:
        return []
    # verificar que la fecha corresponda a un día de atención
    try:
        dt = datetime.fromisoformat(fecha_iso)
        weekday = dt.strftime("%A").lower()  # monday...
        dia_esp = DIAS_ENG_TO_ESP.get(weekday)
    except Exception:
        return []
    if not dia_esp or dia_esp not in doc["dias"]:
        return []
    inicio = doc["inicio"]
    fin = doc["fin"]
    slots = [f"{h:02d}:00" for h in range(inicio, fin)]
    ocupados = [c["hora"] for u, c in CITAS.items() if c.get("doctor") == k and c.get("fecha") == fecha_iso]
    disponibles = [s for s in slots if s not in ocupados]
    return disponibles

# -----------------------
# Citas (por usuario)
# -----------------------
def user_has_appointment(user_key: str) -> bool:
    return user_key in CITAS

def save_appointment(user_key: str, doctor_key: str, fecha_iso: str, hora_str: str) -> bool:
    if not user_key or not doctor_key or not fecha_iso or not hora_str:
        return False
    k = normalize_name(doctor_key)
    disponibles = get_available_slots(k, fecha_iso)
    if hora_str not in disponibles:
        return False
    CITAS[user_key] = {"doctor": k, "fecha": fecha_iso, "hora": hora_str}
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
    doctor_key = cita.get("doctor")
    disponibles = get_available_slots(doctor_key, nueva_fecha)
    if nueva_hora not in disponibles:
        return False
    CITAS[user_key] = {"doctor": doctor_key, "fecha": nueva_fecha, "hora": nueva_hora}
    return True
