import jwt from 'jsonwebtoken'

export function makeToken(user) {
  return jwt.sign(
    { id: user.id, email: user.email, role: user.role, branchId: user.branch_id },
    process.env.JWT_SECRET,
    { expiresIn: '7d' }
  )
}
