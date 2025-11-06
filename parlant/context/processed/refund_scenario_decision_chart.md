# Refund Scenario Decision Chart

This chart provides a structured decision-making process for determining refund eligibility, approval levels, and required documentation.

---

## 🧭 Purpose

To standardize how refund requests are evaluated, ensuring consistency across all customer interactions and minimizing financial risk.

---

## 🧩 Key Decision Factors

| Factor                | Description                              | Example / Notes                                                 |
| :-------------------- | :--------------------------------------- | :-------------------------------------------------------------- |
| **Refund Type**       | Type of refund requested                 | Full, Partial, or Credit                                        |
| **Refund Trigger**    | What caused the refund request           | Overcharge, Service Issue, Duplicate Payment, Canceled Contract |
| **Refund Source**     | Where the refund originated              | Customer Request, Internal Error, Partner Adjustment            |
| **Customer Tier**     | Relationship level with the company      | Standard, Enterprise, Strategic                                 |
| **Approval Required** | Who needs to approve the refund          | Manager, Finance, VP, etc.                                      |
| **Refund Limit ($)**  | Maximum refund allowed per role          | Example: PM ≤ $500, Ops ≤ $1,000, Finance ≤ $5,000              |
| **Documentation**     | What evidence or documentation is needed | Transaction Log, Invoice Copy, Communication Record             |
| **Refund Method**     | How funds are returned                   | Credit Card, ACH, Account Credit, Manual Check                  |

---

## ⚖️ Decision Path

1. **Identify Refund Type**
   - Full refund = High-risk; requires finance sign-off.
   - Partial refund = Case-by-case; manager approval.
   - Credit = Default for minor issues or goodwill gestures.

2. **Confirm Trigger**
   - Verify the event that caused the refund.
   - Gather logs, receipts, or support tickets.

3. **Check Source**
   - If internal → escalate to Operations or Finance.
   - If customer → review service logs or CRM data.

4. **Review Limits**
   - PMs may approve ≤ $500.
   - Ops Managers ≤ $1,000.
   - Director/Finance required above $1,000.

5. **Attach Documentation**
   - Include refund form, screenshots, or communications.

6. **Submit for Approval**
   - Route through approval workflow (TaskRay, Notion, or Formstack).

7. **Log the Decision**
   - Record in refund tracker for audit trail.

---

## 🧾 Example Scenarios

| Scenario                          | Trigger                        | Refund Type | Approval | Notes                                   |
| :-------------------------------- | :----------------------------- | :---------- | :------- | :-------------------------------------- |
| **1. Duplicate Charge**           | Payment processed twice        | Full        | Finance  | Verify via payment processor log        |
| **2. Canceled Before Activation** | Customer canceled before use   | Full        | Manager  | Confirm no service delivery             |
| **3. Partial Service Failure**    | Equipment or API downtime      | Partial     | PM       | Issue partial credit with apology email |
| **4. Goodwill Credit**            | Retention or service recovery  | Credit      | PM       | Used to retain high-value customer      |
| **5. Contractual Adjustment**     | SLA breach or price adjustment | Partial     | Director | Finance to review                       |

---

## 🧮 Formula Reference

```excel
=IF(Refund_Amount <= PM_Limit, "PM Approval",
 IF(Refund_Amount <= Ops_Limit, "Ops Approval",
 IF(Refund_Amount <= Finance_Limit, "Finance Approval", "VP Review")))

# Refund Scenario Decision Chart

This document defines how refund requests should be evaluated and processed. Each scenario describes when it applies, what to verify, what action to take, and how to log it.

---

## Scenario Reference Table

| # | Scenario | Trigger / Condition | Checks | Action | Recognition Phrases / Keywords | Refund Reason / Settings |
|:-:|:--|:--|:--|:--|:--|:--|
| 1 | Authenticate who the user is | Identify who the Account Holder is | Look in Admin for Account Name / Email | If the person calling is not the account holder, we can't take ... a third party service, they are likely a victim of a reseller. | — | — |
| 2 | Product Type Check | Identify if the product is a Transient, Event, or On-demand booking | Look in Admin under "Type". Event bookings will have an event attached to the pass under the start time. | On-Demand products are non-refundable. Event passes usually h...dling scenarios. Transient passes should be handled as usual. | — | — |
| 3 | Merchant of Record Check | Identify who the MOR is on the pass | Look in Admin for MOR field | If MOR = ParkWhiz → process normally. If MOR = AXS → Non-refu...If MOR = SeatGeek → Non-refundable (send back to seller). If MOR = Ticketmaster → Non-refundable (send back to seller). If MOR = Seatgeek → Non-refundable (send back to seller). If MOR = VividSeats → Non-refundable (send back to seller). If MOR = StubHub → Non-refundable (send back to seller). If MOR = TicketNetwork → Non-refundable (send back to seller). If MOR = Gametime → Non-refundable (send back to seller). If MOR = “Resale” / “Reseller” / “3rd Party” → Non-refundable (send back to seller). If MOR = Apple → process normally. If MOR = Google → process normally. If MOR = Waze → process normally. | "merchant of record"; MOR; "purchased through"; "third-party seller"; "not ParkWhiz" | — |
| 4 | Special Handling Check | Identify who the Seller/Location is on the pass | Look in Admin for Seller field | If Seller = Diamond Parking → Enter the refund request on to the Diamond Parking Spreadsheet and submit through Diamond's process. If Seller = ProPark (Bay Area, CA) → Send an email with the refund details to: scott.kellogg@propark.com, jay-li.poon@propark.com, gabriel.iniguezlink@propark.com | — | — |
| 5 | Reseller / Reseller Pass | Pass purchased through a third-party / reseller | Confirm reseller flag in Admin; confirm Seller matches reseller (SeatGeek, StubHub, etc.) | Non-Refundable. Refer to the third party if it is a victim of a reseller. If the reseller is calling, advise of the reseller's status. | "third-party service"; "Seatgeek"; | — |
| 6 | Pre-start time vs. Post | Determine if the pass is considered pre-arrival or post-arrival | Confirm pass start time vs current time in Admin | If pre-arrival, follow Pre-Arrival policy. If post-arrival, document reason for refund and foll[l]ow the respective scenario. | — | — |
| 7 | Was the pass used? | Identify if the pass was used. | Check in Admin under History to see if the pass was used | If pass was used, No refund. | — | — |
| 8 | Season Package Parking | Pass is part of a half/full season package (season passes) | Check if the pass is part of a season package or bundle in Admin | Non-Refundable. (Exception: duplicate packages) | — | — |
| 9 | Pre-Arrival | Pass canceled before start time (unless season / package) | Confirm pass is before start; confirm they did not park | Refund automatically. No lead approval required. | "cancel before start"; "pre-arrival"; "cancel early"; "pre-start" | Refund Reason: Pre-Arrival. Checked: Notify the billing team. Unchecked: Mark as a chargeback (seller's fault) |
| 10 | Oversold | Customer reports location full / oversold | Check ParkWhiz Admin, check location capacity/utilization, check other passes canceled same event | If under $50, refund automatically. If over $50, escalate to Lead. | "garage full"; "lot full"; "no space"; "oversold"; "location full" | Refund Reason: Oversold. Checked: Notify the billing team. Unchecked: Mark as a chargeback (seller's fault) |
| 11 | Duplicate Passes | Multiple passes for same location/date/time (accidental double purchase) | Confirm duplicate purchase in Admin (same event/time/location); confirm only one was used | Refund duplicate pass. Only keep the one they actually used. | "bought twice"; "accidentally purchased twice"; "double charged"; "duplicate booking" | Refund Reason: Duplicate booking. Checked: Notify the billing team. Unchecked: Mark as a chargeback (seller's fault) |
| 12 | Confirmed Rebook | Customer rebooked a new pass (same seller / same event) | Confirm that a later valid booking exists for the same event/location after the failed attempt | Refund the original pass under confirmed rebook. | "I had to rebook"; "bought another pass"; "bought a different pass"; "second booking worked" | Refund Reason: Confirmed Rebook. Checked: Notify the billing team. Unchecked: Mark as a chargeback (seller's fault) |
| 13 | Paid Again | Customer had to pay again onsite | Confirm customer paid again at the same booked location; ask for receipt or confirmation if available | If paid onsite at booked location, refund as Paid Again (no receipt required). If wrong location, issue OTC credit. | "had to pay again"; "they made me pay cash"; "was charged at the gate" | Refund Reason: Paid again. Checked: Notify the billing team. Unchecked: Mark as a chargeback (seller's fault) |
| 14 | Closed Location | Customer reports garage closed (gate down, flooded, power out, etc.) | Call location to verify, ask for photo proof if possible, check if other passes canceled same day | If under $50, refund automatically; if over $50, escalate to Lead | "location closed"; "garage closed"; "gate down"; "elevator broken"; "no lights"; "flooded"; "can't enter" | Refund Reason: Closed. Checked: Notify the billing team. Unchecked: Mark as a chargeback (seller's fault) |
| 15 | Accessibility Issue | Customer unable to access location (road closures, police block, parade, etc.) | Ask which street blocked; confirm on Google Maps / Waze; check Admin notes; see if customer rebooked at alternate location | If under $50, refund automatically; if over $50, escalate to Lead | "road closed"; "blocked street"; "police blocked"; "parade"; "construction"; "can't access garage" | Refund Reason: Accessibility. Checked: Notify the billing team. Unchecked: Mark as a chargeback (seller's fault) |
| 16 | Value of pass | Identify the pass value in ($) | Check value of pass in Admin | Pre-arrival passes may be refunded regardless of the amount (fo... and under should be handled according to each specific scenario | — | — |

---

## Operational Guidance

### Auto-refund (agent can execute without lead/manager)
- Pre-Arrival
- Oversold < $50
- Paid Again (at same booked location)
- Closed Location < $50
- Accessibility Issue < $50
- Confirmed Rebook (original only)

### Requires escalation (lead / manager / finance)
- Any refund > $50 for oversold/closed/access issues
- Season Package Parking (almost always no-refund)
- Reseller / Merchant of Record mismatch
- Anything involving Diamond Parking or ProPark (follow special handling)

### Hard no
- Pass was used
- Third-party / resale where we are not MOR
- Season Package except duplicate buy

---

## Logging Requirements
For any approved refund:
1. Attach screenshots from Admin showing booking details.
2. Attach proof where required (photo of closed gate, rebooked pass, etc.).
3. Mark the correct **Refund Reason** from the table above.
4. Mark "Notify the billing team" if noted in that scenario.
5. Document whether we’re treating it as chargeback/liability on seller.

---

## Policy Notes
- “Under $50” is treated as low-risk and may be refunded directly by agent in most access/oversold/closed scenarios.
- Anything tied to a reseller should be bounced back to reseller. Do not absorb the loss.
- Diamond and ProPark are handled outside normal flow.

---

_Last updated from "Refund Scenario Decision Chart.xlsx" (tab: Refund Scenarios)._
```
