import os
from datetime import datetime
import pytz
from PIL import Image
import piexif
from utils import logger

def extract_gps(image_path):
    """
    Extracts GPS coordinates from an image's EXIF data.
    Returns a dictionary with 'lat' and 'lon' or None if GPS data is unavailable.
    """
    try:
        img = Image.open(image_path)
        exif_data = piexif.load(img.info.get("exif", b""))

        gps_info = exif_data.get("GPS", {})
        if not gps_info:
            logger.info(f"No GPS data found in {image_path}.")
            return None

        def dms_to_decimal(degrees, minutes, seconds, ref):
            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
            if ref in ['S', 'W']:
                decimal *= -1
            return decimal

        lat_data = gps_info.get(piexif.GPSIFD.GPSLatitude)
        lat_ref = gps_info.get(piexif.GPSIFD.GPSLatitudeRef)
        lon_data = gps_info.get(piexif.GPSIFD.GPSLongitude)
        lon_ref = gps_info.get(piexif.GPSIFD.GPSLongitudeRef)

        if lat_data and lat_ref and lon_data and lon_ref:
            lat = dms_to_decimal(*[val[0] / val[1] for val in lat_data], lat_ref.decode())
            lon = dms_to_decimal(*[val[0] / val[1] for val in lon_data], lon_ref.decode())
            return {"lat": lat, "lon": lon}
        else:
            logger.info(f"Incomplete GPS data in {image_path}.")
            return None

    except Exception as e:
        logger.error(f"Error extracting GPS metadata from {image_path}: {e}")
        return None

def extract_timestamp(filepath):
    """
    Extracts the timestamp from the image metadata and converts it to UTC.
    """
    try:
        img = Image.open(filepath)
        exif_data = img._getexif()

        if exif_data is not None:
            timestamp_str = exif_data.get(36867)  # 36867 is the DateTimeOriginal tag
            if timestamp_str:
                # Parse the local timestamp (assuming the camera stores it in local time)
                local_timestamp = datetime.strptime(timestamp_str, "%Y:%m:%d %H:%M:%S")

                # Convert local time to UTC
                local_tz = pytz.timezone('Europe/Stockholm')
                local_timestamp = local_tz.localize(local_timestamp)
                utc_timestamp = local_timestamp.astimezone(pytz.utc)

                return utc_timestamp
    except Exception as e:
        logger.error(f"Error extracting timestamp from {filepath}: {e}")

    return None