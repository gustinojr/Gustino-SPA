import os
import qrcode

# Use your Render URL here, e.g., "https://gustino-spa.onrender.com/"
site_url = os.environ.get("SITE_URL", "https://gustino-spa.onrender.com/")

qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=10,
    border=4,
)
qr.add_data(site_url)
qr.make(fit=True)

img = qr.make_image(fill_color="black", back_color="white")
img.save("gustino_coupon_qr.png")
print(f"✅ QR code saved as gustino_coupon_qr.png (URL: {site_url})")
