"""EVM supply sink semantics shared by replay and reconciliation paths.

See ``references/playbook-supply-recon.md`` for the authoritative definitions:
form 1 is a contract-level burn that reduces ``totalSupply``; form 2 transfers
tokens into an inaccessible sink while ``totalSupply`` remains unchanged.

Transfer events alone cannot distinguish a true burn from a deposit when
``to`` is one of the sink addresses.  That distinction requires comparison
with the on-chain ``totalSupply`` scalar at the same frozen block.
"""

# Transfer's zero-address sentinel is also a potential balance sink.
ZERO = "0x0000000000000000000000000000000000000000"
DEAD = "0x000000000000000000000000000000000000dead"

# Replay records burn_total for these recipients but still credits their balances.
REPLAY_BALANCE_SINKS = (ZERO, DEAD)
