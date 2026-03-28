"""Shared test fixtures."""

import pytest


@pytest.fixture
def sample_chapter_text() -> str:
    return """\
Chapter 1: The Storm Approaches

The wind howled through the narrow streets of the old fishing village,
rattling the shutters and sending loose debris tumbling across the cobblestones.
Dark clouds gathered on the horizon, swallowing the last traces of sunlight.
The fishermen had long since pulled their boats ashore, lashing them to the
weathered posts that lined the harbor.

Old Martha stood at her window, watching the sky with knowing eyes. She had
seen storms like this before — fifty years ago, when the great wave had swept
away half the village. The air tasted of salt and something else, something
electric and dangerous. Her hands trembled as she drew the curtains closed.

In the tavern at the end of the pier, a dozen souls huddled around the fire.
They spoke in hushed tones about the barometer reading and the strange behavior
of the seabirds that morning. Captain Reed nursed his whiskey in silence, his
weathered face betraying nothing of the worry that gnawed at his insides. He
had lost his son to the sea, and he knew better than anyone that the ocean
took what it wanted, when it wanted.

Chapter 2: Safe Harbor

The morning after the storm broke clear and golden. Sunlight streamed through
every window, warming the wooden floors and chasing away the shadows of the
night before. Children emerged from their houses like spring flowers, running
barefoot through puddles that shimmered with reflected sky.

The damage was less than feared. A few shingles missing here, a toppled fence
there, but the boats were safe and the harbor wall had held. The village
breathed a collective sigh of relief. Mrs. Chen opened her bakery early, and
the smell of fresh bread drifted through the streets like a benediction.

Captain Reed walked the shore alone, his boots leaving deep prints in the
wet sand. For the first time in years, he smiled. The sea had been merciful,
and perhaps — just perhaps — it was time to forgive it. He picked up a smooth
stone and turned it over in his palm, then skipped it across the calm water,
counting the bounces like a boy again.

Chapter 3: New Beginnings

Word spread quickly that the old lighthouse was being restored. A young
architect from the city had purchased it, drawn by photographs she had seen
in a travel magazine. Her name was Elena, and she arrived on a Tuesday with
a van full of blueprints and an irrepressible enthusiasm that the villagers
found both charming and slightly suspicious.

She set up her drafting table in the lighthouse keeper's cottage, which had
stood empty for a decade. The walls were thick with ivy and the roof leaked
in three places, but Elena saw only possibility. She hired local workers and
threw herself into the project with an energy that seemed inexhaustible.

The lighthouse became the talk of the village. Every day, curious residents
would find some excuse to walk past and observe the progress. Slowly, the
old tower shed its decay, revealing the elegant bones beneath. Fresh paint,
new glass, restored ironwork — the lighthouse was coming back to life, and
somehow, so was the village itself.
"""


@pytest.fixture
def short_text() -> str:
    return "This is a very short text that should not be split."


@pytest.fixture
def no_chapter_text() -> str:
    return """\
The forest was dark and silent. Not the comfortable silence of a sleeping house,
but the watchful silence of something holding its breath. Every shadow seemed to
have weight and substance, pressing in from all sides.

She walked carefully, placing each foot with deliberate precision on the mossy
ground. The path had disappeared two miles back, swallowed by undergrowth that
seemed to grow thicker with every step. Her flashlight beam cut a thin corridor
through the darkness, illuminating nothing but more trees, more shadows, more of
the endless green.

The compass in her pocket was useless here. Something about these woods confused
it — perhaps the iron deposits in the granite bedrock, or perhaps something else
entirely. She navigated by instinct and by the distant sound of running water,
which she hoped was the river that would lead her back to the road.

After what felt like hours, the trees began to thin. Moonlight filtered through
the canopy, casting silver patterns on the ground. She emerged into a clearing
and stopped short. Before her stood a cottage, small and neat, with smoke curling
from its chimney and warm light glowing in every window. It was impossible — she
had studied the maps thoroughly, and there was no building for ten miles in any
direction. Yet here it was, real and solid and inviting.

She hesitated at the gate. Every fairy tale she had ever read warned against
entering such places. But the night was cold, and the forest was vast, and the
warm light was so very welcoming. She pushed open the gate and walked up the path
to the front door, and knocked three times.
"""
