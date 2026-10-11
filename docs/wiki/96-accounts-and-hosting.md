# 96 — Accounts and hosting

> Status: design-spec — the model as the operator stated it on 2026-10-08, with an
> **as-built ledger** (every row checked on disk that day) so the page cannot describe
> as done a thing the code does not do. The pages that are normative for the pieces
> that exist are named in each row.
>
> [← Overview](00-overview-and-glossary.md)

This page answers four questions the public site has to answer without guessing: what
an account is for, what a hosted instance is and what it costs, who the registrar is and
whether it has to be, and which of that is built.

## The model, stated

- **The software needs no account.** An instance you run holds its own records at its
  own address, and nothing about it reaches anyone.
- **An account is a person's sign-in, and it is free.** It exists for one thing: reaching
  instances that someone else runs — your own, hosted for you, or the instance of an
  organization you belong to. An organization hosted by a provider gives its people
  their own sign-ins to that organization's instance; the people pay nothing.
- **A hosted instance is the thing that costs**, and only for what it occupies: the
  storage, compute and traffic of the instance and of the custom applications hosted
  for a person or an organization. The figures are read from the host's own price list,
  on the host, never typed into a page — the same discipline the public site follows
  for the release number.
- **Services are ports an instance employs, not things it depends on.** Mail, website
  hosting and payment processing are port extensions (`92-ports-as-four-layers.md`);
  an instance is set to use them and can be set not to. A hosted client's instance uses
  the host's services through the `fnd_service` extension.
- **The registrar is a decision.** Anyone can host a local instance and still take part
  in the broader network. Any other party can choose to act as the central registrar
  and set its own standard of agreement. For ease of adoption, Fruitful Network
  Development runs the registry micyte.com reads and publishes the catalogue every
  instance pulls (`../contracts/tool_package_update_contract.md`).
- **Who maintains what.** The MiCyte software, micyte.com and its resources are
  maintained by Fruitful Network Development, which operates within its site-based
  hosting and development to provide its clients their services. The software's public
  home is the MiCyte GitHub organization (`MiCyte/MiCyte`, with `MiCyte/TXA` and
  `MiCyte/Registrar` documenting the taxonomy and the registrar's datums, since
  2026-10-09); micyte.com may eventually run on its own server, with FND's server keeping
  the provided services. `../standards/release_and_versioning.md` lists where the
  organization's name lives.

## As built, 2026-10-11

| the model says | built? | what the code does, and where |
|---|---|---|
| the software needs no account | **yes** | `micyte/` registers tools, channels and packages with no identity provider; `93-the-marketplace.md` |
| a person signs in | **hosted clients only** | Keycloak behind an auth proxy; the host trusts the proxy's headers (`fnd_app/instances/_shared/portal_host/app.py`). Sign-ins are created and reset by the operator through `fnd_app/instances/_shared/portal_host/fnd_routes/grantee_signin.py`, one Keycloak group per hosted client. Nobody can create their own sign-in. |
| an organization's people have their own sign-ins | **partly** | several sign-ins per group, with two roles, `full` and `finance` (read-only), resolved in `app.py`. Opened by the operator. |
| an account is free | **yes, as a capped instance (2026-10-09)** | the operator's rule: "a free account is an instance, simply capped at minimal storage". The host's door (`fnd_app/instances/_shared/portal_host/fnd_routes/signup.py`) files a `plan: free` reservation and asks for no card; `fnd_app/instances/_shared/runtime/grantee_provisioning.py` runs the identity, sign-in, roster, document and instance steps and records the four books steps as not needed; the free tier IS the absence of a `base_service` subscription (`instance_account.tier_of_services`). The free allowance (`FREE_DATUM_MB`, no website files) is ENFORCED: `datum_write_authorization.StorageAllowanceExceeded` at the one gate every grantee write passes, and `FndSiteAdapter.upload_asset` through the host's `allowance` callable; both answer with a sentence that names the allowance and the upgrade. The operator still establishes the instance (`onboard_base_account.py --tier free`, Keycloak group, portal stopped). |
| finishing an account online | **built, unbound** | The fill is PayPal's Vault (operator, 2026-10-09: "same simple PayPal use"): `fnd_app/packages/peripherals/commerce/paypal_vault.py` behind the port, registered as the host extension `paypal_vault` (`fnd_app/instances/_shared/grantor/paypal_fill.py`), resolved by the host through the binding's own fill. `POST /__fnd/signup/complete` vaults once `fnd_app/scripts/bind_payment_instrument.py` has bound the fill with FND's own PayPal credential (sandbox first) and `instrument.vault` is granted; until then it answers 503 and the operator finishes with `fnd_app/scripts/onboard_base_account.py`. The monthly charge is `fnd_app/instances/_shared/runtime/grantor_billing.py` (`fnd_app/scripts/bill_hosted_accounts.py`), run as `automation:grantor_billing`. |
| a client is one identity | **two addresses** | a hosted client is a grantee msn that authenticates and an instance msn that holds the books (`fnd_app/packages/grantee_services/fnd_service/credential.py`, `fnd_app/instances/_shared/runtime/instance_account.py`). |
| the upgrade from the free account | **requested from PIM, applied by the operator (2026-10-09)** | Home's "Your plan" names the base account at the offering's price and a form posts `/__fnd/pim/account/upgrade`; the ask is filed 0600 (`fnd_app/instances/_shared/runtime/account_upgrade_runtime.py`) because a grantee writes none of the grantor's books. The operator subscribes, records the month and the card (the signup door with `?card=1` vaults one for an established account). |
| a person's account on the network | **not built** | network participation is per instance (`../contracts/hosted_alias_interface.md`, `../contracts/contract_formation.md`); person-level accounts are step 8 of `90-network-contract-architecture.md`, after discovery and magnet resolution. |
| storage and traffic are what is charged | **priced, displayed; the FREE allowance enforced (2026-10-09), the base allowances still legible only** | the service nodes and their prices are minted into the grantor's offering (`fnd_app/scripts/bootstrap_grantor_services.py`, `fnd_app/scripts/_applied/price_grantor_services.py`, written through `fnd_app/instances/_shared/runtime/ledger_write_runtime.py`); a bundle's included storage is `INCLUDED_SITE_GB` / `INCLUDED_DATUM_GB` in `instance_account.py`, shown by `micyte/tools/pim_overview.py`. Nothing refuses a write or throttles a connection at the *base* allowances. Traffic is read from the web server's logs for cost attribution only (`fnd_app/instances/_shared/runtime/utilities_extensions/tolling.py`). |
| services are ports the instance employs | **yes, for hosted clients** | `fnd_service` in `micyte/tools/_packages.py` fills `email_provider` and `site_hosting`; its credential is the login, not a key (`credential.py`). |
| a non-hosted instance employs the host's services with a key | **door yes, binding no** | the host accepts the key at `POST /__fnd/service/<site|mail|mailbox>/<action>` (`fnd_app/instances/_shared/portal_host/fnd_routes/service_api.py`): verified by recomputation (`grantor_keys.py`), the grantee claim built by the door, the alias's own grants judging each operation, the client door's mailbox words only. The instance's half is `micyte/adapters/hosted/` (a transport that authorizes before it sends, a 0600 credential, site and mail adapters built `from_credential`). Not yet an extension in the catalogue: a portal's Ports surface cannot build these adapters, and listing one it cannot build would advertise a choice that does nothing. |
| the registrar is a parameter | **library yes, host no** | `micyte/domains/registry/engine.py` takes the registrar as `authority_msn_id`; peers resolve from the contact card's signature and endpoint fields. The host sets `DEFAULT_AUTHORITY_MSN_ID` in `fnd_app/instances/_shared/runtime/network_surfaces.py` and publishes its endpoint with `fnd_app/scripts/denote_instance_endpoint.py`; no configuration key names another registrar (`../contracts/port_binding_store.md` lists the keys). |
| an instance keeps its registry card by declaring it | **yes** | the default contract's payload (`../contracts/contract_formation.md`, *The declaration*): an instance signs the card projected from its `msn_profile` and sends it to the registrar (`fnd_app/scripts/declare_instance_card.py`); the registrar applies it under a key it can check, or queues it for its operator (`/portal/api/v2/registry/declarations`). `add_registrar_card_fields.py` no longer rebuilds an existing registry. |
| another party can run a registrar with its own rules | **the handshake, yes; discovery, no** | `../contracts/registrar_residency.md` and `../contracts/contract_formation.md` are as-built; discovery without a contract (`msn_registry`, step 6 of `90-network-contract-architecture.md`) is not, and no delivery between two live instances has happened. |

## What the model needs that is not built

1. **Self-serve establishment of the free account.** The door files it and the operator
   establishes it (a Keycloak group per account, the portal stopped for the store write).
   "Present by default" needs an automation path that mints the two addresses under a
   chosen house, creates the group and converges the instance without stopping the portal.
2. **The payment-instrument fill, BOUND**: the fill exists (PayPal); the operator binds FND's PayPal REST credential, sandbox first, proves one exchange, then live.
3. **A registrar configuration key on the host**, replacing the constant, so "a decision
   rather than a default" is a setting somebody can change.
4. **Person-level accounts on the network** (step 8 of
   `90-network-contract-architecture.md`), after discovery and magnet resolution.
5. **Enforcement at the base allowances**, if those are to be caps too. The free allowance
   is enforced (2026-10-09); the base amounts remain a legible bundle. The datum figure the
   gate reads is at most five minutes old by design (`storage_facts`' memo), so a burst
   inside that window can pass the allowance by the burst.
6. **The key's binding on the instance's side.** The door accepts service keys
   (2026-10-09) and `micyte/adapters/hosted/` speaks to it; what remains is declaring the
   hosted adapters as an extension once a portal's mail and site constructors can build
   them from a hosted credential, and a per-alias rate (the per-IP one is nginx's).
   Payments are not offered through a key.

## What the public site may say, and how

micyte.com states the model and this ledger's verdicts in plain words: an account is free
and what it is for; a hosted instance is charged for the hardware behind it; the host
states every figure; the registrar need not be FND; and what is not built yet is said to
be not built yet. It types no price and no plan (the decision of 2026-10-04: the
commercial offer lives on the host, in the private tree, where it is read from the
offering), and it links the host's door as a link rather than a button, because the
site stands when the portal does not.
