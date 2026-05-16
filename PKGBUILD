# Maintainer: KlapkiSzatana
pkgname=serwis-app
pkgver=3.0.0
pkgrel=1
pkgdesc="Proste Prowadzenie Serwisu"
arch=('any')
url="https://github.com/KlapkiSzatana/serwis-app"
license=('GPL-3.0')

depends=('python' 'pyside6' 'python-cryptography' 'python-pillow' 'python-requests')
optdepends=('python-barcode: obsługa kodów kreskowych na wydrukach')

source=("serwis-app.py"
        "serwisapp.png")

sha256sums=('d340b8cf38f05a1f252313f6ef30b10c2ac45b8ecf63b2d2f701f6a9b4cb7e34'
            '4e98f7e73d667f695ef6430db3c1877f47b76ad504fd3a1eba69937ac047ff72')

package() {
    install -d "${pkgdir}/usr/share/${pkgname}"

    install -m644 "${srcdir}/serwis-app.py" "${pkgdir}/usr/share/${pkgname}/"
    install -m644 "${srcdir}/serwisapp.png" "${pkgdir}/usr/share/${pkgname}/"

    for dir in actions fonts modules setup ui resources; do
        if [ -d "${startdir}/${dir}" ]; then
            cp -r "${startdir}/${dir}" "${pkgdir}/usr/share/${pkgname}/"
        fi
    done

    find "${pkgdir}/usr/share/${pkgname}" -type d -name '__pycache__' -prune -exec rm -r {} +
    find "${pkgdir}/usr/share/${pkgname}" -type d -exec chmod 755 {} +
    find "${pkgdir}/usr/share/${pkgname}" -type f -exec chmod 644 {} +

    install -Dm644 "${srcdir}/serwisapp.png" "${pkgdir}/usr/share/pixmaps/${pkgname}.png"

    install -d "${pkgdir}/usr/bin"
    cat <<EOF > "${pkgdir}/usr/bin/${pkgname}"
#!/bin/sh
cd /usr/share/${pkgname}
exec /usr/bin/python serwis-app.py "\$@"
EOF
    chmod 755 "${pkgdir}/usr/bin/${pkgname}"

    install -Dm644 /dev/stdin "${pkgdir}/usr/share/applications/${pkgname}.desktop" <<EOF
[Desktop Entry]
Name=SerwisApp
GenericName=Proste Prowadzenie Serwisu
Exec=/usr/bin/${pkgname}
Icon=${pkgname}
Terminal=false
Type=Application
Categories=Office;Utility;
StartupWMClass=serwis-app
StartupNotify=true
EOF
}
