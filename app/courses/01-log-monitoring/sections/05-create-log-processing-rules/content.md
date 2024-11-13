## Log Processing Rules
As part of log ingestion pipeline, log records ingested via Generic Log ingestion or OneAgent, can be processed with Processing Rules to slice and dice them, enrich the data or filter out unwanted records.

Some common situations in which log processing rules are use

- Very often logs come in a myriad number of formats. Logs from one service or process at one host can be different to the others 

- Different attributes or data in logs can have different relevancy for different teams.

- Parsing (extracting output fields from input log records) can be complicated or resource-expensive when done on the source.

Through log processeing, we can process all logs sent to Dynatrace cluster. Numerical attributes, strings, dates, IP-addresses, arrays, JSON objects and other data can be extracted as fields from raw log records. This allows creating metrics or events based on extracted fields, conduct torubleshooting, include thes in Davis root cause, ...

The processing of logs is done via hierachical (evaluated from top to bottom) log processing rules.

A processing Rule definition consists of a left-to-right sequence of processing commands chained together using the pipe character (`|`). 


Log Processing rules consist in a matcher (which defines the scope of log records to be processed) and a processor definition (which defines the processing to be done on the different fields of the subset of matching records).

The following commands are available:
- **PARSE** - Parses the input into a structured data stream.
- **USING** - Filters the input based on the specified condition.
- **FIELDS_ADD** - Enrich the input with additional data.
- **FIELDS_RENAME** - Adds annotations to the input.
- **FIELDS_REMOVE** - Removes fields from the input.
- **FILTER_OUT** - Filters out the input based on the specified condition.


Commands take parameters as optional arguments. Depending on the command, these parameters can be static values or the output from expressions and functions.
The following type of functions are available as parameters to the commands:
- **Bitwise operations**
- **Boolean**
- **Casting**
- **Comparison**
- **Composite-data**
- **Cryptographic**
- **Date-time**
- **Flow-control**
- **Math**
- **Network**
- **Strings**
- **Other**

A comprehensive list of functions and parameters can be found [here](https://dt-url.net/processing-rules-functions).

*It is important to note that functions and operators accept only declared types of data. The type is assigned to all input fields defined by the USING command as well as to the variables created while parsing or using the casting functions*


___
# Dynatrace Pattern Language
One of the most typical usecases of log processing rules is to extract data from log record fields into new fileds or to create metrics or events based on the extracted data. 

Extracting data from log records is done by using the `PARSE` command, which takes as parameters the field that we want to parse and a string with a pattern that describes the data we want to extract.

Pattterns are described using the Dynatrace Pattern Language, which is a powerful way to describe  describe patterns using matchers.

A matcher is a mini-pattern that matches a certain type of data. For example, INTEGER (or INT) matches integer numbers, and IPADDR matches IPv4 or IPv6 addresses. There are matchers available to handle all kinds of data types.

A written pattern is interpreted from left to right, ignoring extra whitespaces, line breaks, and comments in between. You can write the pattern describing an integer followed by a single space, IP address, and line break as the following one-liner:


```DPL
INT ' ' IPADDR:ip EOL
```
Which can also be written as:
```DPL
/* this pattern expects an integer number and an IP address
    separated by single space in each line */

INT       //an integer
' '       //followed by single space
IPADDR:ip //followed by IPv4 or IPv6 address, extracted as a new field, `ip`
EOL       //line is terminated with line feed character
```

DPL can be used to match your data in a flexible way and to extract it to new fields by appending `:fieldname` to the matcher if you want to store the extracted data into a new field.
![DPL example](./images/dpl-ref-2133-49fd05dd03.png){width=100%}

<br/>
<br/>
___
<br/>
# Creating Log Processing Rules
<br/>
## Parsing fields from records using the PARSE command
<br/>
###Example 1: Parse out specific fields from JSON content

In this example, the logs are pushed into Dynatrace as JSON objects with the following content field:

```JSON
{
  "content": "{\"intField\": 13, \"stringField\": \"someValue\", \"nested\": {\"nestedStringField1\": \"someNestedValue1\", \"nestedStringField2\": \"someNestedValue2\"} }"
}
```

    Parsing field from JSON in flat mode.
    You can use a JSON matcher and configure it to extract desired fields as top-level log attributes. The matcher in flat mode creates attributes automatically and names them exactly the same as the corresponding JSON field names.

    You can then use the FIELDS_RENAME command to set the names that fit you.

    Processing rule definition:

PARSE(content, "JSON{STRING:stringField}(flat=true)")

| FIELDS_RENAME(better.name: stringField)

Result after transformation:

{

  "content": "{\"intField\": 13, \"stringField\": \"someValue\", \"nested\": {\"nestedStringField1\": \"someNestedValue1\", \"nestedStringField2\": \"someNestedValue2\"} }",

  "better.name": "someValue"

}

Parsing nested field from JSON.
You can also parse more fields (including nested ones) using a JSON matcher without flat mode. As a result, you get a VariantObject that you can process further. For example, you can create a top-level attribute from its inner fields.

Processing rule definition:

PARSE(content, "

JSON{

  STRING:stringField,

  JSON {STRING:nestedStringField1}:nested

}:parsedJson")

| FIELDS_ADD(top_level.attribute1: parsedJson["stringField"], top_level.attribute2: parsedJson["nested"]["nestedStringField1"])

| FIELDS_REMOVE(parsedJson)

Result after transformation:

{

  "content": "{\"intField\": 13, \"stringField\": \"someValue\", \"nested\": {\"nestedStringField1\": \"someNestedValue1\", \"nestedStringField2\": \"someNestedValue2\"} }",

  "top_level.attribute1": "someValue",

  "top_level.attribute2": "someNestedValue1"

}

Parsing all fields from JSON in auto-discovery mode.
Sometimes you're interested in all of the JSON fields. You don't have to list all of the attributes. Instead, a JSON matcher can be used in auto-discovery mode. As a result, you get a VARIANT_OBJECT that you can process further. For example, you can create a top-level attribute from its inner fields.

Processing rule definition:

PARSE(content,"JSON:parsedJson")

| FIELDS_ADD(f1: parsedJson["intField"],

f2:parsedJson["stringField"],

f3:parsedJson["nested"]["nestedStringField1"],

f4:parsedJson["nested"]["nestedStringField2"])

| FIELDS_REMOVE(parsedJson)

Result after transformation:

{

  "content": "{\"intField\": 13, \"stringField\": \"someValue\", \"nested\": {\"nestedStringField1\": \"someNestedValue1\", \"nestedStringField2\": \"someNestedValue2\"} }",

  "f1": "13",

  "f2": "someValue",

  "f3": "someNestedValue1",

  "f4": "someNestedValue2"

}

Parsing any field from JSON, treating content like plain text.
With this approach, you can name the attribute as you lik, but the processing rule is more complex.

Processing rule definition:

PARSE(content, "LD '\"stringField\"' SPACE? ':' SPACE?  DQS:newAttribute ")

Result after transformation:

{

  "content": "{\"intField\": 13, \"stringField\": \"someValue\", \"nested\": {\"nestedStringField1\": \"someNestedValue1\", \"nestedStringField2\": \"someNestedValue2\"} }",

  "newAttribute": "someValue"

}

Example 5: Parse out attributes from different formats

You can parse out attributes from different formats within a single pattern expression.

In this example, one or more applications is logging a user identifier that you want to extract as a standalone log attribute. The log format is not consistent because it includes various schemes to log the user ID:

    user ID=
    userId=
    userId:
    user ID =

With the optional modifier (question ?) and Alternative Groups, you can cover all such cases with a single pattern expression:

PARSE(content, "

  LD //matches any text within a single line

  ('user'| 'User') //user or User literal

  SPACE? //optional space

  ('id'|'Id'|'ID') //matches any of these

  SPACE? //optional space

  PUNCT? //optional punctuation

  SPACE? //optional space

  INT:my.user.id

")

Using such a rule, you can parse out the user identifier from many different notations. For example:

03/22 08:52:51 INFO user ID=1234567 Call = 0319 Result = 0
03/22 08:52:51 INFO UserId = 1234567 Call = 0319 Result = 0
03/22 08:52:51 INFO user id=1234567 Call = 0319 Result = 0
03/22 08:52:51 INFO user ID:1234567 Call = 0319 Result = 0
03/22 08:52:51 INFO User ID: 1234567 Call = 0319 Result = 0
03/22 08:52:51 INFO userid: 1234567 Call = 0319 Result = 0
Example 6: Multiple PARSE commands within a single processing rule

You can handle various formats or perform additional parsing on already parsed-out attributes with multiple PARSE commands connected with pipes (|).

For example, with the following log:

{

  "content": "{\"intField\": 13, \"message\": \"Error occurred for user 12345: Missing permissions\", \"nested\": {\"nestedStringField1\": \"someNestedValue1\", \"nestedStringField2\": \"someNestedValue2\"} }"

}

First, you can parse out the message field, the user ID, and the error message.

PARSE(content, "JSON{STRING:message}(flat=true)") | PARSE(message, "LD 'user ' INT:user.id ': ' LD:error.message")

The result is:

{

  "content": "{\"intField\": 13, \"message\": \"Error occurred for user 12345: Missing permissions\", \"nested\": {\"nestedStringField1\": \"someNestedValue1\", \"nestedStringField2\": \"someNestedValue2\"} }",

  "message": "Error occurred for user 12345: Missing permissions",

  "user.id": "12345",

  "error.message": "Missing permissions"

}

Example 7: Use specialized matchers

We provide a comprehensive list of matchers that ease pattern building.

For example, you can parse the following sample log event:

{

  "content":"2022-05-11T13:23:45Z INFO 192.168.33.1 \"GET /api/v2/logs/ingest HTTP/1.0\" 200"

}

using the specialized matchers:

PARSE(content, "ISO8601:timestamp SPACE UPPER:loglevel SPACE IPADDR:ip SPACE DQS:request SPACE INTEGER:code")

and the result is:

{

  "content": "2022-05-11T13:23:45Z INFO 192.168.33.1 \"GET /api/v2/logs/ingest HTTP/1.0\" 200",

  "timestamp": "1652275425000",

  "loglevel": "INFO",

  "ip": "192.168.33.1",

  "request": "GET /api/v2/logs/ingest HTTP/1.0",

  "code": "200"

}
