# Refund Policy - Condensed for AI Decision Making

## Core Rules

### Refund Limits
- Agent limit: $50 (auto-approve)
- Over $50: Escalate to human
- **Exception**: Pre-arrival refunds have NO limit

### Time Restrictions
- Refunds must be within 14 days of pass end date
- **Exception**: Duplicate passes can be refunded anytime

### Non-Refundable Categories
1. **Reseller passes** (except seller/event cancellations)
2. **Season packages** (except duplicates)
3. **On-demand products**
4. **Used passes** (check History in Admin)
5. **Third-party MOR**: AXS, SeatGeek, StubHub (refer to seller)

### Merchant of Record (MOR) Rules
- **ParkWhiz MOR**: Process normally
- **Ticketmaster/Groupon**: Process normally (no credits for Groupon)
- **Third-party MOR** (AXS, SeatGeek, StubHub): Non-refundable, refer to seller
- **Partner MOR** (Google, Waze, Apple, Edenred): Process normally

---

## Auto-Approve Scenarios (Under $50)

### 1. Pre-Arrival
**Trigger**: Cancellation before pass start time  
**Action**: Auto-refund (no limit)  
**Exceptions**: Season passes, reseller passes, cancellation restrictions

### 2. Duplicate Passes
**Trigger**: Same location/date/time, purchased within minutes  
**Checks**: Verify both passes, confirm which to keep  
**Action**: Refund duplicate  
**Refund Reason**: "Duplicate" (tech error) or "Confirmed Rebook" (user error)

### 3. Confirmed Rebook
**Trigger**: Customer rebooked with same seller/location  
**Checks**: Verify new booking exists, old pass unused  
**Action**: Refund original pass

### 4. Oversold (Under $50)
**Trigger**: Location full, customer turned away  
**Checks**: 
- Check for other oversold refunds same date
- Verify customer rebooked elsewhere
**Action**: Auto-refund if under $50

### 5. Paid Again (At Booked Location)
**Trigger**: Customer paid onsite at correct location  
**Checks**: Confirm correct location, not wrong location  
**Action**: Refund (no receipt required)  
**Note**: If wrong location → OTC credit instead

### 6. Closed Location (Under $50)
**Trigger**: Gate down, flooded, power out, elevator broken  
**Checks**: Look for other passes canceled same reason  
**Action**: Auto-refund if under $50

### 7. Accessibility Issue (Under $50)
**Trigger**: Road closed, police blockade, construction  
**Checks**: Verify on Google Maps/Waze, check for rebook  
**Action**: Auto-refund if under $50

---

## Escalate to Human (Over $50 or Complex)

### Oversold, Closed, Accessibility Over $50
**Action**: Escalate with verification details

### Special Handling Sellers
- **Diamond Parking**: Enter on refund sheet, await approval
- **NYC locations (Parking Management)**: Email nyc@parkwhiz.com
- **City Parking**: Only for Paid Again with written no-dispute confirmation
- **Tampa Sports Authority**: Email for approval
- **Olympia Development**: 3-hour cancellation restriction

### Multi-Day Partial Refunds
**Action**: Always escalate to Lead  
**Note**: Must charge first 24 hours + buyer fee

### Monthly Parking (After Start Date)
**Action**: Email POC or nyc@parkwhiz.com for approval

### Poor Experience / Damage / Theft
**Action**: Do NOT refund - refer to location, escalate if needed

### Missing Amenity / Inaccurate Hours / Attendant Refused
**Action**: Escalate to appropriate team (DSS, DSImp)

---

## Decision Tree

```
1. Check MOR → Third-party? → Refer to seller
2. Check if used → Used? → No refund
3. Check if reseller → Reseller? → No refund (except seller cancellation)
4. Check if season package → Season? → No refund (except duplicate)
5. Check timing → Pre-arrival? → Auto-refund
6. Check scenario → Duplicate/Rebook/Oversold/Paid Again/Closed/Access?
   → Under $50? → Auto-refund
   → Over $50? → Escalate
7. All other cases → Escalate to human
```

---

## Key Verification Steps

### For Oversold/Closed/Accessibility
1. Check for similar reports (other refunds same date/location)
2. Verify customer at correct location
3. Check if customer rebooked

### For Paid Again
1. Confirm correct location (not wrong location)
2. Ask amount paid onsite
3. Verify not early arrival/late departure violation

### For Duplicates
1. Same location, date, time
2. Purchased within minutes
3. Verify which pass to keep
4. Check if tech error or user error

---

## Refund Reason Codes

- **Pre-Arrival**: Before start time
- **Duplicate**: Tech/system error
- **Confirmed Rebook**: User error duplicate or intentional rebook
- **Oversold**: Location at capacity
- **Paid Again**: Had to pay onsite at booked location
- **Closed**: Location closed/inaccessible
- **Accessibility**: Road/access blocked

---

## Quick Reference: Can AI Handle?

**YES (Auto-approve under $50)**:
- Pre-arrival (any amount)
- Duplicate passes
- Confirmed rebook
- Oversold < $50
- Paid again (correct location) < $50
- Closed < $50
- Accessibility < $50

**NO (Escalate to human)**:
- Any refund > $50 (except pre-arrival)
- Special handling sellers
- Multi-day partial refunds
- Monthly parking (after start)
- Poor experience / damage / theft
- Missing amenity / inaccurate hours
- Season packages (except duplicate)
- Reseller passes
- Used passes
- Third-party MOR
