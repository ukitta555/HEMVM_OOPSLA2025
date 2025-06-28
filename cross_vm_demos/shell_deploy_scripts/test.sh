#!/bin/bash
ACCOUNTS=2
for ((idx=1;idx<ACCOUNTS;idx++)) do
    aptos key generate --output-file ./keys.txt
done