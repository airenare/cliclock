# Maintainer: air <airenare@gmail.com>
pkgname=cliclock
pkgver=0.1.0
pkgrel=1
pkgdesc='A terminal clock (Python, stdlib only)'
arch=('any')
url='https://localhost/cliclock'
# No LICENSE file is shipped yet; replace with a real SPDX id once one is added.
license=('custom')
depends=('python')
options=(!strip !debug)

# Local build from this checkout: nothing is downloaded.
prepare() {
    mkdir -p "$srcdir/cliclock" "$srcdir/docs" "$srcdir/packaging"
    install -m 0644 "$startdir"/cliclock/*.py "$srcdir/cliclock/"
    install -m 0644 "$startdir/README.md" "$srcdir/README.md"
    install -m 0644 "$startdir/docs/INTERFACES.md" "$srcdir/docs/INTERFACES.md"
    install -m 0755 "$startdir/packaging/cliclock" "$srcdir/packaging/cliclock"
}

package() {
    local lib="$pkgdir/usr/lib/cliclock"
    install -d "$lib/cliclock" "$lib/docs" "$pkgdir/usr/bin"
    install -m 0644 "$srcdir"/cliclock/*.py "$lib/cliclock/"
    install -m 0644 "$srcdir/README.md" "$lib/README.md"
    install -m 0644 "$srcdir/docs/INTERFACES.md" "$lib/docs/INTERFACES.md"
    install -m 0755 "$srcdir/packaging/cliclock" "$pkgdir/usr/bin/cliclock"
}

# README: two ways to install this checkout
#   system-wide package:  makepkg -si
#   user-level, no root:  ./install.sh        (sudo ./install.sh => /usr/local)
