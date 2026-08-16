import GlassLogin from '../components/auth/GlassLogin'

export default function Login({ onSuccess, onGoRegister }) {
  return <GlassLogin onSuccess={onSuccess} onGoRegister={onGoRegister} />
}
