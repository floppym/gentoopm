EAPI=4

DESCRIPTION="A installable test ebuild"

SLOT="0"
IUSE="example-flag"

S=${WORKDIR}

src_install() {
	touch "${ED%/}"/.test
}
