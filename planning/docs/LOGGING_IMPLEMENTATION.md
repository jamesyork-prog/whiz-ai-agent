# Logging Implementation Summary

## Overview

Comprehensive logging has been added to all policy-based decision components to provide visibility into the decision-making process, aid in debugging, and support monitoring and auditing.

## Logging Configuration

**Location:** `parlant/main.py`

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
```

This configuration provides:
- Timestamp for each log entry
- Component name (module) that generated the log
- Log level (INFO, WARNING, ERROR)
- Descriptive message

## Components with Logging

### 1. PolicyLoader (`parlant/tools/policy_loader.py`)

**Logs Added:**
- **Startup:** Policy document loading from context directory
- **Success:** Successful parsing of JSON policy files
- **Warnings:** JSON parsing failures (falls back to raw content)
- **Success:** Markdown file loading with character counts
- **Completion:** All policies loaded successfully
- **Errors:** Missing required policy files

**Example Output:**
```
2025-11-14 16:55:55 - app_tools.tools.policy_loader - INFO - Loading policy documents from: /app/app_tools/context/processed
2025-11-14 16:55:55 - app_tools.tools.policy_loader - INFO - Successfully loaded refund_scenario_decision_chart.md (11808 chars)
2025-11-14 16:55:55 - app_tools.tools.policy_loader - INFO - All policy documents loaded successfully
```

### 2. BookingExtractor (`parlant/tools/booking_extractor.py`)

**Logs Added:**
- **Start:** Beginning of extraction process
- **Input validation:** Empty ticket notes warning
- **Debug:** Ticket notes length
- **Method selection:** Pattern vs LLM extraction
- **Pattern results:** Success/failure with confidence level
- **Pattern details:** HTML vs text detection
- **LLM calls:** API invocation with model name
- **LLM results:** Extraction success with found fields
- **Warnings:** Multiple bookings detected
- **Errors:** Timeouts, JSON parsing errors, API failures

**Example Output:**
```
2025-11-14 16:55:55 - app_tools.tools.booking_extractor - INFO - Starting booking information extraction
2025-11-14 16:55:55 - app_tools.tools.booking_extractor - INFO - Attempting pattern-based extraction
2025-11-14 16:55:55 - app_tools.tools.booking_extractor - INFO - Pattern extraction succeeded with medium confidence. Found: ['booking_id', 'event_date', 'location', 'amount']
```

### 3. RuleEngine (`parlant/tools/rule_engine.py`)

**Logs Added:**
- **Start:** Beginning of rule application
- **Debug:** Booking info summary (ID, date, type)
- **Validation:** Missing event date warnings
- **Calculation:** Days before event
- **Rule matching:** Which specific rule matched
- **Decision:** Final decision with confidence
- **Warnings:** Edge cases with no matching rules

**Example Output:**
```
2025-11-14 16:55:55 - app_tools.tools.rule_engine - INFO - Applying rule-based decision logic
2025-11-14 16:55:55 - app_tools.tools.rule_engine - INFO - Days before event: -325
2025-11-14 16:55:55 - app_tools.tools.rule_engine - INFO - Post-event cancellation detected (325 days after)
2025-11-14 16:55:55 - app_tools.tools.rule_engine - INFO - Rule matched: Post-Event Cancellation. Decision: Denied
```

### 4. LLMAnalyzer (`parlant/tools/llm_analyzer.py`)

**Logs Added:**
- **Start:** Beginning of LLM analysis
- **Debug:** Model name being used
- **Context:** Rule-based result availability
- **API call:** Gemini API invocation
- **Timing:** Processing time in milliseconds
- **Results:** Decision, confidence, policy applied
- **Debug:** Key factors influencing decision
- **Fallback:** Using rule-based decision when LLM fails
- **Errors:** Timeouts, JSON parsing, validation errors, API failures

**Example Output:**
```
2025-11-14 16:55:55 - app_tools.tools.llm_analyzer - INFO - Starting LLM analysis for complex case
2025-11-14 16:55:55 - app_tools.tools.llm_analyzer - INFO - Rule-based result available: Uncertain (confidence: low)
2025-11-14 16:55:55 - app_tools.tools.llm_analyzer - INFO - LLM analysis completed in 1234ms. Decision: Approved, Confidence: high, Policy: Pre-Arrival Cancellation
```

### 5. DecisionMaker (`parlant/tools/decision_maker.py`)

**Logs Added:**
- **Start:** Beginning of decision process with ticket ID
- **Extraction:** Booking info extraction status
- **Validation:** Missing critical fields
- **Rule application:** Invoking rule engine
- **Rule results:** Decision and confidence from rules
- **LLM invocation:** When and why LLM is called
- **LLM results:** Decision from LLM analysis
- **Fallback:** Using rule-based decision when LLM fails
- **Cancellation mapping:** Mapping to ParkWhiz reason
- **Completion:** Final decision, method used, processing time
- **Errors:** All error types with context

**Example Output:**
```
2025-11-14 16:55:55 - app_tools.tools.decision_maker - INFO - Starting decision-making process for ticket: TEST-001
2025-11-14 16:55:55 - app_tools.tools.decision_maker - INFO - Using pre-extracted booking info
2025-11-14 16:55:55 - app_tools.tools.decision_maker - INFO - Applying rule-based decision logic
2025-11-14 16:55:55 - app_tools.tools.decision_maker - INFO - Rule-based result: Denied (confidence: high)
2025-11-14 16:55:55 - app_tools.tools.decision_maker - INFO - Rule-based decision has sufficient confidence, skipping LLM analysis
2025-11-14 16:55:55 - app_tools.tools.decision_maker - INFO - Decision-making complete. Decision: Denied, Method: rules, Processing time: 0ms
```

## Log Levels Used

### INFO
- Normal operation flow
- Successful operations
- Decision outcomes
- Processing milestones

### WARNING
- Recoverable issues (e.g., JSON parsing failures with fallback)
- Missing optional data
- Edge cases
- Multiple bookings detected

### ERROR
- Failed operations
- Missing required data
- API failures
- Timeouts
- Validation errors

### DEBUG
- Detailed technical information
- Input data summaries
- Intermediate calculations
- API parameters

## Monitoring Use Cases

### 1. Performance Monitoring
Track processing times:
```
grep "Processing time:" logs | awk '{print $NF}' | sort -n
```

### 2. Decision Method Distribution
See how often rules vs LLM is used:
```
grep "Method:" logs | awk '{print $NF}' | sort | uniq -c
```

### 3. Error Tracking
Monitor failures:
```
grep "ERROR" logs
```

### 4. Confidence Analysis
Track decision confidence levels:
```
grep "confidence:" logs
```

### 5. Rule Matching
See which rules are most commonly matched:
```
grep "Rule matched:" logs | sort | uniq -c
```

## Requirements Satisfied

This implementation satisfies the following requirements from task 11:

✅ **Add logging for policy loading (startup)**
- PolicyLoader logs all file loading operations
- Success/failure for each policy document
- Character counts for loaded files

✅ **Add logging for booking extraction (confidence, found/not found)**
- Extraction method (pattern vs LLM)
- Confidence levels (high/medium/low)
- Found fields list
- Errors and timeouts

✅ **Add logging for rule application (which rules matched)**
- Days before event calculation
- Specific rule that matched
- Decision and confidence
- Edge cases and warnings

✅ **Add logging for LLM analysis (decision, confidence, processing time)**
- Analysis start/completion
- Processing time in milliseconds
- Decision, confidence, policy applied
- Key factors
- Fallback scenarios

✅ **Add logging for errors and timeouts**
- All error types logged with context
- Timeout handling in extraction and analysis
- Fallback decision logging
- Error recovery paths

## Testing

Run the logging verification test:
```bash
docker-compose exec parlant python /app/test_logging_verification.py
```

This test exercises all components and displays their logging output.
