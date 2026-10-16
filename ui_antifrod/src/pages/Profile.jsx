import React, { useRef, useState } from 'react';
import { authApi } from '@/api/auth';
import { useAuth } from '@/libs/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Lock, LogOut, Loader2, Camera, Shield } from 'lucide-react';

export default function Profile() {
  const { user, logout, setUser } = useAuth();
  const fileInput = useRef(null);
  const [avatarBusy, setAvatarBusy] = useState(false);
  const [avatarError, setAvatarError] = useState('');
  const [avatarMessage, setAvatarMessage] = useState('');

  const changeAvatar = async (file) => {
    setAvatarError('');
    setAvatarMessage('');
    if (file && file.size > 5 * 1024 * 1024) {
      setAvatarError('Фото должно быть не больше 5 МБ');
      return;
    }
    setAvatarBusy(true);
    try {
      setUser(await (file ? authApi.uploadAvatar(file) : authApi.deleteAvatar()));
      setAvatarMessage(file ? 'Фото сохранено' : 'Фото удалено');
    } catch (err) {
      setAvatarError(err.message || 'Не удалось обновить фото');
    } finally {
      setAvatarBusy(false);
    }
  };
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const roleLabel = 'Оператор';
  const initial = user?.email?.[0]?.toUpperCase() || '?';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');

    if (newPassword.length < 6) {
      setError('Пароль должен быть не короче 6 символов');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Пароли не совпадают');
      return;
    }

    setLoading(true);
    try {
      await authApi.changePassword(oldPassword, newPassword);
      setMessage('Пароль успешно изменён');
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setError(err.message || 'Не удалось сменить пароль');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">Профиль</p>
        <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">Ваш аккаунт</h1>
      </header>

      <section className="rounded-2xl border border-border bg-card p-6">
        <div className="flex items-center gap-5">
          <div className="relative">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-accent text-2xl font-semibold text-accent-foreground">
              {user?.avatar_url ? <img src={user.avatar_url} alt="Фото профиля" className="h-full w-full rounded-full object-cover" /> : initial}
            </div>
            <button
              type="button"
              className="absolute -bottom-1 -right-1 flex h-8 w-8 items-center justify-center rounded-full border border-border bg-background text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              title="Загрузить фото"
              aria-label="Загрузить фото"
              disabled={avatarBusy}
              onClick={() => fileInput.current?.click()}
            >
              {avatarBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Camera className="h-4 w-4" />}
            </button>
          </div>
          <div className="min-w-0">
            <p className="truncate text-base font-medium text-foreground">{user?.email}</p>
            <p className="mt-1 inline-flex items-center gap-1.5 text-xs text-muted-foreground">
              <Shield className="h-3.5 w-3.5" />
              {roleLabel}
            </p>
          </div>
        </div>

        <input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" aria-label="Файл фото профиля"
          onChange={(e) => { const file = e.target.files?.[0]; e.target.value = ''; if (file) changeAvatar(file); }} />
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button variant="outline" disabled={avatarBusy} onClick={() => fileInput.current?.click()}>
            {avatarBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Camera className="h-4 w-4" />}
            {user?.avatar_url ? 'Заменить фото' : 'Загрузить фото'}
          </Button>
          {user?.avatar_url && <Button variant="ghost" disabled={avatarBusy} onClick={() => changeAvatar(null)}>Удалить фото</Button>}
          <span className="text-xs text-muted-foreground">JPEG, PNG или WebP · до 5 МБ</span>
        </div>
        {avatarError && <p role="alert" className="mt-3 text-sm text-destructive">{avatarError}</p>}
        {avatarMessage && <p role="status" className="mt-3 text-sm text-accent-foreground">{avatarMessage}</p>}

        <dl className="mt-6 space-y-3 border-t border-border pt-5 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Email</dt>
            <dd className="font-mono">{user?.email}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Роль</dt>
            <dd>{roleLabel}</dd>
          </div>
          {user?.full_name && (
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Имя</dt>
              <dd>{user.full_name}</dd>
            </div>
          )}
        </dl>

        <Button variant="outline" className="mt-6" onClick={() => logout()}>
          <LogOut className="h-4 w-4" /> Выйти из аккаунта
        </Button>
      </section>

      <section className="rounded-2xl border border-border bg-card p-6">
        <h2 className="font-display text-lg font-semibold">Смена пароля</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Введите текущий пароль и новый. После смены войдите заново.
        </p>

        {error && (
          <div className="mt-4 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
        )}
        {message && (
          <div className="mt-4 rounded-lg bg-accent p-3 text-sm text-accent-foreground">{message}</div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div className="space-y-2">
            <Label htmlFor="old">Текущий пароль</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="old"
                type="password"
                autoComplete="current-password"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                className="pl-10 h-12"
                required
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="new">Новый пароль</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="new"
                type="password"
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="pl-10 h-12"
                required
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm">Повторите новый пароль</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="confirm"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="pl-10 h-12"
                required
              />
            </div>
          </div>
          <Button type="submit" disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Сохранение…
              </>
            ) : (
              'Сменить пароль'
            )}
          </Button>
        </form>
      </section>
    </div>
  );
}
