from hypothesis import settings

# Property tests draw the same examples on every run, so CI cannot fail at random, and slow
# machines cannot trip a deadline.
settings.register_profile("repeatable", derandomize=True, deadline=None)
settings.load_profile("repeatable")
