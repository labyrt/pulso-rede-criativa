import unicodedata


def _field(identifier: str, value: str) -> str:
    return f"{identifier}{len(value):02d}{value}"


def _ascii(value: str, limit: int) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return normalized.upper().strip()[:limit]


def _crc16(payload: str) -> str:
    polynomial = 0x1021
    result = 0xFFFF
    for byte in payload.encode("utf-8"):
        result ^= byte << 8
        for _ in range(8):
            result = ((result << 1) ^ polynomial) & 0xFFFF if result & 0x8000 else (result << 1) & 0xFFFF
    return f"{result:04X}"


def build_pix_payload(key: str, receiver_name: str, city: str, amount=None, description="Apoio PULSO") -> str:
    merchant = _field("00", "BR.GOV.BCB.PIX") + _field("01", key.strip())
    if description:
        merchant += _field("02", _ascii(description, 72))
    payload = _field("00", "01")
    payload += _field("26", merchant)
    payload += _field("52", "0000")
    payload += _field("53", "986")
    if amount:
        payload += _field("54", f"{amount:.2f}")
    payload += _field("58", "BR")
    payload += _field("59", _ascii(receiver_name, 25))
    payload += _field("60", _ascii(city, 15))
    payload += _field("62", _field("05", "***"))
    payload += "6304"
    return payload + _crc16(payload)
