# Maintainer: Aamir Abdullah <aamirabdullah33@gmail.com>
# Contributor: PKOS Linux Team

pkgname=pkos-mirrorlist-manager
pkgver=2.0.0
pkgrel=1
pkgdesc="A modern GUI application for managing Arch Linux mirror lists - Built for PKOS Linux"
arch=('any')
url="https://github.com/pkos-linux/mirrorlist-manager"
license=('MIT')
depends=('python' 'python-pyqt6' 'python-requests' 'python-setuptools')
makedepends=('python-build' 'python-installer' 'python-wheel')
optdepends=(
    'sudo: for system mirrorlist modifications'
    'polkit: for GUI privilege escalation'
)
source=("$pkgname-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")
sha256sums=('SKIP')  # Update with actual checksum

build() {
    cd "$pkgname-$pkgver"
    python -m build --wheel --no-isolation
}

package() {
    cd "$pkgname-$pkgver"
    python -m installer --destdir="$pkgdir" dist/*.whl
    
    # Install desktop file
    install -Dm644 pkos-mirrorlist-manager.desktop \
        "$pkgdir/usr/share/applications/pkos-mirrorlist-manager.desktop"
    
    # Install documentation
    install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
    
    # Create symlinks for easy execution
    mkdir -p "$pkgdir/usr/bin"
    ln -s "/usr/lib/python*/site-packages/main_improved.py" \
        "$pkgdir/usr/bin/pkos-mirrorlist-manager"
    ln -s "/usr/lib/python*/site-packages/main.py" \
        "$pkgdir/usr/bin/pkos-mirrorlist-manager-classic"
}

# Package information
# Developer: Aamir Abdullah
# Email: aamirabdullah33@gmail.com
# License: Open Source (MIT)
# Built for: PKOS Linux Distribution