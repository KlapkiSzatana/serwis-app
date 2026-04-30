# Maintainer: Heisenberg (KlapkiSzatana)
pkgname=serwis-app
pkgver=2.3.0
pkgrel=1
pkgdesc="Proste Prowadzenie Serwisu - Kompleksowe zarządzanie serwisem"
arch=('any')
url="https://github.com/KlapkiSzatana/serwis-app"
license=('GPL-3.0')

depends=('python' 'pyside6' 'python-cryptography' 'python-pillow' 'python-requests')
optdepends=('python-barcode: obsługa kodów kreskowych na wydrukach')

# Wymieniamy tylko PLIKI. Foldery zostaną skopiowane bezpośrednio z katalogu roboczego.
source=("serwis-app.py"
        "serwisapp.png"
        "icon.png")

# Teraz updpkgsums zadziała, bo widzi tylko te 3 pliki
sha256sums=('931768dcdbb4e2cb91ed02a823fe8961fcca45265b2a940dc0c59789faceab60'
            'd97eac85821ff29650c1d517ba843d91948d7f85bfcec2c552e1e093f90a4111'
            'fb0a5349e2be3d9fc051c0768c03a30008fd422025eddc838c05b4d9d5af0c03')

package() {
    install -d "${pkgdir}/usr/share/${pkgname}"

    # 1. Instalacja plików głównych z ${srcdir}
    install -m644 "${srcdir}/serwis-app.py" "${pkgdir}/usr/share/${pkgname}/"
    install -m644 "${srcdir}/serwisapp.png" "${pkgdir}/usr/share/${pkgname}/"
    install -m644 "${srcdir}/icon.png" "${pkgdir}/usr/share/${pkgname}/"

    # 2. Instalacja wszystkich podkatalogów bezpośrednio z folderu budowania (${startdir})
    # To rozwiązuje problem "nie znaleziono w źródłach"
    for dir in actions fonts modules setup ui resources; do
        if [ -d "${startdir}/${dir}" ]; then
            cp -r "${startdir}/${dir}" "${pkgdir}/usr/share/${pkgname}/"
        fi
    done

    # 3. Czyszczenie i uprawnienia
    find "${pkgdir}/usr/share/${pkgname}" -type d -name '__pycache__' -prune -exec rm -r {} +
    find "${pkgdir}/usr/share/${pkgname}" -type d -exec chmod 755 {} +
    find "${pkgdir}/usr/share/${pkgname}" -type f -exec chmod 644 {} +

    # 4. Ikona systemowa
    install -Dm644 "${srcdir}/serwisapp.png" "${pkgdir}/usr/share/pixmaps/${pkgname}.png"

    # 5. Skrypt startowy
    install -d "${pkgdir}/usr/bin"
    cat <<EOF > "${pkgdir}/usr/bin/${pkgname}"
#!/bin/sh
cd /usr/share/${pkgname}
exec /usr/bin/python serwis-app.py "\$@"
EOF
    chmod 755 "${pkgdir}/usr/bin/${pkgname}"

    # 6. Desktop file
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
