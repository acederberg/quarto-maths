# stsart snippet solution
class Solution:
    def minSwaps(self, s: str) -> int:
        
        unbalanced = 0
        opening = 0

        for char in s:
            if char == "[":
                opening += 1
                continue

            if opening:
                opening -= 1
            else:
                unbalanced += 1

        return (unbalanced + 1) // 2
        # end snippet solution

