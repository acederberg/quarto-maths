# start snippet solution_trivial
class SolutionTrivial:

    def shortestPalindrome(self, s: str):

        n = len(s)
        if n <= 1:
            return s

        best_init = 0
        for k in range(n, 0, -1):
            if (t := s[0:k]) == t[::-1]:
                best_init = k
                break

        mantisa = s[best_init:]
        return mantisa[::-1] + s

    # stop snippet trivial
