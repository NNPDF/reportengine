This is a test with title {@title@}
===================================

{@world@}

{@with l@}
### Another title, inside l: {@title@}
Yet world stays the same:
{@world@}

But can get repeated:
{@l::nested world@}

Can nest even more:
{@with l::nested@}
####{@title@}
See?
{@endwith@}

This was the previous title: {@title@}

{@ endwith @}

And this the original title {@title@}.

Done.