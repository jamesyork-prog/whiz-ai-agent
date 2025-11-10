# AI vs. Human Refund Scenarios

This document outlines which refund scenarios are best handled by an AI agent and which require human intervention, based on the rules and guidelines in the `refund_guide.json`, `refund_rules.json`, and `refund_senario_decision_chart.md` documents.

---

## Scenarios Well-Suited for AI Agent

These scenarios are ideal for an AI agent because they are based on clear, objective rules and data that can be accessed and processed programmatically.

### Gates/Decision Points

These are preliminary checks that the AI can perform to determine the correct refund path. They do not typically result in a direct refund but are crucial for routing the request.

| Scenario                           | Description                                                           | Why AI is a good fit                                                 |
| :--------------------------------- | :-------------------------------------------------------------------- | :------------------------------------------------------------------- |
| **Authenticate who the user is**   | Verify the identity of the account holder.                            | Simple data lookup and verification.                                 |
| **Product Type Check**             | Determine if the product is a transient, event, or on-demand booking. | Straightforward data lookup in the admin system.                     |
| **Merchant of Record (MOR) Check** | Identify the MOR for the transaction.                                 | Clear, rule-based logic with defined actions for each MOR.           |
| **Reseller / Reseller Pass**       | Check for a reseller flag.                                            | Simple data lookup and a clear "Non-Refundable" rule.                |
| **Pre-start time vs. Post**        | Determine if the request is before or after the pass start time.      | Simple date and time comparison.                                     |
| **Was the pass used?**             | Check if the pass has been used.                                      | Straightforward check of the pass history.                           |
| **Season Package Parking**         | Determine if the pass is part of a season package.                    | Simple check for a season package and a clear "Non-Refundable" rule. |
| **Value of pass**                  | Identify the value of the pass.                                       | Simple data lookup of the pass value.                                |

### Scenarios that End in a Refund

These scenarios can be fully handled by an AI agent, from the initial request to the final refund.

| Scenario                            | Description                                                     | Why AI is a good fit                                                   |
| :---------------------------------- | :-------------------------------------------------------------- | :--------------------------------------------------------------------- |
| **Pre-Arrival**                     | The customer cancels before the pass start time.                | The AI can automatically process the refund if the conditions are met. |
| **Duplicate Passes**                | The customer was charged for the same pass multiple times.      | The AI can identify and refund the duplicate pass.                     |
| **Confirmed Rebook**                | The customer rebooked a new pass with the same seller/location. | The AI can verify the rebooking and refund the original pass.          |
| **Oversold (under $50)**            | The location was full, and the pass value is under $50.         | The AI can process the refund automatically based on the value.        |
| **Paid Again (at booked location)** | The customer paid again at the booked location.                 | The AI can process the refund.                                         |

---

## Scenarios Better Suited for Human Engagement

These scenarios require subjective judgment, complex interactions, or actions that are not easily automated.

| Scenario                          | Description                                                                                  | Why a human is a better fit                                                                                               |
| :-------------------------------- | :------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------ |
| **Special Handling Check**        | The seller requires special handling for refunds.                                            | Requires sending emails to external contacts and creating Freshdesk tickets, which is better handled by a human.          |
| **Closed Location**               | The customer reports that the location was closed.                                           | Requires calling the location to verify the closure, which is a human task.                                               |
| **Accessibility Issue**           | The customer was unable to access the location due to road closures or other issues.         | Requires calling the garage and using external tools like Waze or Google Maps in a more nuanced way.                      |
| **Oversold (escalations)**        | The pass value is over $50.                                                                  | Requires human approval for the refund.                                                                                   |
| **Paid Again (OTC credit)**       | The customer paid at the wrong location and is requesting an "Other Than Cash" (OTC) credit. | Issuing an OTC credit may require human judgment to assess the situation and the customer's history.                      |
| **Poor Experience**               | The customer had a bad experience at the location.                                           | Requires subjective judgment to determine the appropriate action (refund, credit, or referral).                           |
| **Inaccurate Hours of Operation** | The location's hours of operation were incorrect.                                            | Requires creating a ticket for the seller support team and potentially following up, which is better handled by a human.  |
| **Missing Amenity**               | An advertised amenity was missing at the location.                                           | Requires creating a ticket for the implementations team and potentially following up, which is better handled by a human. |
| **Multi-Day Partial Refunds**     | The customer is requesting a partial refund for a multi-day pass.                            | Requires human judgment and should not be promised without consulting a lead.                                             |
| **Monthly Parking Refunds**       | The customer is requesting a refund for a monthly pass after the start date.                 | Requires emailing the appropriate contact for approval, which is better handled by a human.                               |
