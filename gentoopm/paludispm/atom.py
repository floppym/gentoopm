#!/usr/bin/python
#	vim:fileencoding=utf-8
# (c) 2011 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import paludis, re

from gentoopm.basepm.atom import PMAtom, PMPackageKey, PMPackageVersion, \
		PMIncompletePackageKey
from gentoopm.exceptions import InvalidAtomStringError

_category_wildcard_re = re.compile(r'\w')

class PaludisPackageKey(PMPackageKey):
	def __init__(self, key):
		self._k = key

	@property
	def category(self):
		return str(self._k.category)

	@property
	def package(self):
		return str(self._k.package)

	def __str__(self):
		return str(self._k)

class PaludisIncompletePackageKey(PMIncompletePackageKey):
	def __init__(self, key):
		self._k = key

	@property
	def package(self):
		return str(self._k)

class PaludisPackageVersion(PMPackageVersion):
	def __init__(self, ver):
		self._v = ver

	@property
	def without_revision(self):
		return str(self._v.remove_revision())

	@property
	def revision(self):
		rs = self._v.revision_only()
		assert(rs.startswith('r'))
		return int(rs[1:])

	def __str__(self):
		return str(self._v)

	def __lt__(self, other):
		return self._v < other._v

class PaludisAtom(PMAtom):
	def _init_atom(self, s, env, wildcards = False):
		opts = paludis.UserPackageDepSpecOptions() \
				+ paludis.UserPackageDepSpecOption.NO_DISAMBIGUATION
		if wildcards:
			opts += paludis.UserPackageDepSpecOption.ALLOW_WILDCARDS

		try:
			self._atom = paludis.parse_user_package_dep_spec(
					s, env, opts,
					paludis.Filter.All())
		except (paludis.BadVersionOperatorError, paludis.PackageDepSpecError,
				paludis.RepositoryNameError):
			raise InvalidAtomStringError('Incorrect atom: %s' % s)

	def __init__(self, s, env, block = ''):
		self._incomplete = False
		self._blocking = block
		if isinstance(s, paludis.PackageDepSpec):
			self._atom = s
		else:
			try:
				self._init_atom(s, env)
			except InvalidAtomStringError:
				# try */ for the category
				self._init_atom(_category_wildcard_re.sub(r'*/\g<0>', s, 1), env, True)
				self._incomplete = True
		self._env = env

	def __contains__(self, pkg):
		# we have to implementing matching by hand, boo
		other = pkg.atom
		# 1) category, our may be unset
		if self.key.category is not None \
				and self.key.category != other.key.category:
			return False
		# 2) package name
		if self.key.package != other.key.package:
			return False
		# 3) package version (if any requirement set)
		try:
			vr = next(iter(self._atom.version_requirements))
		except StopIteration:
			pass
		else:
			if not vr.version_operator.compare(pkg._pkg.version,
					vr.version_spec):
				return False
		# 4) slot
		if self.slot is not None \
				and self.slot != other.slot:
			return False
		# 5) repository
		if self.repository is not None \
				and self.repository != other.repository:
			return False
		return True

	def __str__(self):
		if self._incomplete:
			raise ValueError('Unable to stringify incomplete atom')
		return '%s%s' % (self._blocking, str(self._atom))

	@property
	def complete(self):
		return not self._incomplete

	@property
	def key(self):
		if self.complete:
			return PaludisPackageKey(self._atom.package)
		else:
			return PaludisIncompletePackageKey(self._atom.package_name_part)

	@property
	def version(self):
		try:
			vr = next(iter(self._atom.version_requirements))
		except StopIteration:
			return None
		return PaludisPackageVersion(vr.version_spec)

	@property
	def slot(self):
		if self._atom.slot_requirement is None:
			return None
		return str(self._atom.slot_requirement.slot)

	@property
	def repository(self):
		if self._atom.in_repository is None:
			return None
		return str(self._atom.in_repository)
