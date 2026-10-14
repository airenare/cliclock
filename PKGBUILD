# Maintainer: Anton Bakulin <airenare@gmail.com>
pkgname=cliclock
pkgver=0.2.0
pkgrel=1
pkgdesc='A terminal clock with big ASCII digits in six styles (Python, stdlib only)'
arch=('any')
url='https://github.com/airenare/cliclock'
license=('MIT')
depends=('python')
options=(!strip !debug)

# Builds from this checkout (nothing is downloaded): makepkg -si

package() {
    local lib="$pkgdir/usr/lib/cliclock"
    install -d "$lib/cliclock" "$pkgdir/usr/bin"
    install -m 0644 "$startdir"/cliclock/*.py "$lib/cliclock/"
    install -m 0755 "$startdir/packaging/cliclock" "$pkgdir/usr/bin/cliclock"
    install -Dm 0644 "$startdir/LICENSE" "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
