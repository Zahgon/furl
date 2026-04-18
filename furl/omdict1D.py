# -*- coding: utf-8 -*-

#
# furl - URL manipulation made simple.
#
# Ansgar Grunseid
# grunseid.com
# grunseid@gmail.com
#
# License: Build Amazing Things (Unlicense)
#

from orderedmultidict import omdict

from .common import is_iterable_but_not_string, absent as _absent


class omdict1D(omdict):

    """
    One dimensional ordered multivalue dictionary. Whenever a list of
    values is passed to set(), __setitem__(), add(), update(), or
    updateall(), it's treated as multiple values and the appropriate
    'list' method is called on that list, like setlist() or
    addlist(). For example:

      omd = omdict1D()

      omd[1] = [1,2,3]
      omd[1] != [1,2,3] # True.
      omd[1] == 1 # True.
      omd.getlist(1) == [1,2,3] # True.

      omd.add(2, [2,3,4])
      omd[2] != [2,3,4] # True.
      omd[2] == 2 # True.
      omd.getlist(2) == [2,3,4] # True.

      omd.update([(3, [3,4,5])])
      omd[3] != [3,4,5] # True.
      omd[3] == 3 # True.
      omd.getlist(3) == [3,4,5] # True.

      omd = omdict([(1,None),(2,None)])
      omd.updateall([(1,[1,11]), (2,[2,22])])
      omd.allitems == [(1,1), (1,11), (2,2), (2,22)]
    """

    def add(self, key, value):
        pass

    def set(self, key, value):
        pass

    def __setitem__(self, key, value):
        return self._set(key, value)

    def _bin_update_items(self, items, replace_at_most_one,
                          replacements, leftovers):
        """
        Subclassed from omdict._bin_update_items() to make update() and
        updateall() process lists of values as multiple values.

        <replacements> and <leftovers> are modified directly, ala pass by
        reference.
        """
        pass

    def _set(self, key, value):
        pass
