# Self-healing

State machine: detected → prompt_composed → heal_requested → awaiting_approval → validating → approved|rejected → verifying → closed_healed|escalated.

Five-level preview validator: `backend/app/heal/validator.py`. Verification run is the hard gate (`ARCHITECTURE.md` §5.8).
